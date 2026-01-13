"""Company Research Tool - Streamlit Web Application.

A demo application for researching companies for legitimacy assessment,
shell company detection, and sanctions screening.
"""

import json
import os
import sys
from io import BytesIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BRAVE_API_KEY, OPENCORPORATES_API_TOKEN
from data.loaders import load_fraud_dataset, load_ofac_names, get_dataset_stats
from enrichment.enrichment_pipeline import EnrichmentPipeline
from scoring.risk_scorer import RiskScorer
from ui.charts import (
    create_risk_gauge,
    create_category_breakdown,
    create_risk_distribution,
    create_source_breakdown,
    create_fraud_type_pie,
    create_jurisdiction_chart,
    highlight_risk_row,
    highlight_status_row,
)
from ui.network_viz import (
    load_demo_network,
    create_pyvis_network,
    create_cluster_subgraph,
    filter_by_node_type,
    get_connected_entities,
    compute_network_metrics,
)
from utils.exceptions import ValidationError
from utils.session_state import AnalysisState, initialize_session_state


# Page config
st.set_page_config(
    page_title="Company Research Tool",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


# Initialize session state on app start
initialize_session_state()


def home_page():
    """Render the home page."""
    st.title("Company Research Tool")
    st.markdown("### Automated Legitimacy Assessment & KYC Compliance")

    st.markdown(
        """
    This tool helps investigators quickly assess companies for potential
    shell company indicators, fraud risk, and sanctions exposure. It combines
    data from multiple sources to provide comprehensive risk assessments.

    **Features:**
    - Upload Excel/CSV files with company lists
    - Enrich data via Brave Search & OpenCorporates APIs
    - Calculate risk scores using weighted framework
    - Browse known fraud cases database
    - Screen against OFAC sanctions lists
    - **NEW:** Interactive network visualization for fraud investigation
    - Export results to Excel/CSV

    **Data Sources:**
    - **SEC Enforcement Actions** - Fraud cases and litigation
    - **SEC Complaint PDFs** - Extracted defendant information
    - **OpenSanctions OFAC** - US Treasury sanctions data
    - **Brave Search** - Online presence verification
    - **OpenCorporates** - Global corporate registry data

    **Risk Scoring Framework:**
    - **Online Activity (30%)**: Website presence, social media, Wikipedia
    - **Corporate Info (25%)**: Status, lifespan, registered address
    - **Officers & Structure (20%)**: Officer count, address matching
    - **Jurisdiction Risk (15%)**: High-risk offshore locations
    - **External Factors (10%)**: Regulatory mentions, data confidence
    """
    )

    # Quick stats - use cached loaders
    st.markdown("---")
    st.markdown("### Database Statistics")

    stats = get_dataset_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if stats["fraud_cases"]["loaded"]:
            st.metric("Fraud Cases", stats["fraud_cases"]["count"])
        else:
            st.metric("Fraud Cases", 0)
    with col2:
        if stats["fraud_cases"]["loaded"]:
            fraud_df = load_fraud_dataset()
            real_cases = len(fraud_df[~fraud_df["is_synthetic"]])
            st.metric("Real Cases", real_cases)
        else:
            st.metric("Real Cases", 0)
    with col3:
        if stats["ofac_names"]["loaded"]:
            st.metric("OFAC Names", stats["ofac_names"]["count"])
        else:
            st.metric("OFAC Names", "Not loaded")
    with col4:
        if stats["fraud_cases"]["loaded"]:
            fraud_df = load_fraud_dataset()
            jurisdictions = fraud_df["jurisdiction"].nunique()
            st.metric("Jurisdictions", int(jurisdictions))
        else:
            st.metric("Jurisdictions", 0)

    # Source breakdown
    fraud_df = load_fraud_dataset()
    if fraud_df is not None and len(fraud_df) > 0:
        st.markdown("### Data Source Breakdown")
        source_counts = fraud_df['source'].value_counts()
        st.plotly_chart(
            create_source_breakdown(source_counts),
            use_container_width=True
        )

    # API status
    st.markdown("---")
    st.markdown("### API Configuration Status")

    col1, col2 = st.columns(2)
    with col1:
        if BRAVE_API_KEY:
            st.success("✅ Brave Search API: Configured")
        else:
            st.warning("⚠️ Brave Search API: Not configured (using mock data)")

    with col2:
        if OPENCORPORATES_API_TOKEN:
            st.success("✅ OpenCorporates API: Configured")
        else:
            st.warning("⚠️ OpenCorporates API: Not configured (using mock data)")


def upload_analyze_page():
    """Render the upload and analyze page."""
    st.title("Upload & Analyze Companies")

    # File upload
    uploaded_file = st.file_uploader(
        "Upload Excel or CSV file with company names",
        type=["xlsx", "xls", "csv"],
        help="File should have a column with company names",
    )

    if uploaded_file is not None:
        # Load file
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.success(f"Loaded {len(df)} companies from {uploaded_file.name}")

            # Column selection
            st.markdown("### Column Mapping")
            col1, col2 = st.columns(2)

            with col1:
                name_col = st.selectbox(
                    "Company Name Column",
                    options=df.columns.tolist(),
                    index=0 if "Company Name" not in df.columns else df.columns.tolist().index("Company Name"),
                )

            with col2:
                jur_cols = ["(None)"] + df.columns.tolist()
                jur_col = st.selectbox(
                    "Jurisdiction Column (optional)",
                    options=jur_cols,
                    index=0 if "Jurisdiction" not in df.columns else jur_cols.index("Jurisdiction"),
                )

            # Preview
            st.markdown("### Data Preview")
            st.dataframe(df.head(10), use_container_width=True)

            # Analyze button
            if st.button("🔍 Analyze Companies", type="primary"):
                analyze_companies(
                    df,
                    name_col,
                    jur_col if jur_col != "(None)" else None,
                )

        except Exception as e:
            st.error(f"Error loading file: {e}")

    else:
        # Show sample format
        st.markdown("### Expected File Format")
        st.markdown(
            """
        Your file should have at minimum a column with company names.
        Optionally include a jurisdiction column (e.g., 'us_de', 'gb', 'sg').

        Example:
        """
        )
        sample_df = pd.DataFrame(
            {
                "Company Name": [
                    "Apple Inc.",
                    "Global Ventures Ltd.",
                    "Pacific Holdings PTE",
                ],
                "Jurisdiction": ["us_ca", "ky", "sg"],
            }
        )
        st.dataframe(sample_df, use_container_width=True)


def analyze_companies(df: pd.DataFrame, name_col: str, jur_col: str = None):
    """Run enrichment and scoring on uploaded companies."""
    st.markdown("---")
    st.markdown("### Analysis Progress")

    # Initialize pipeline and scorer
    pipeline = EnrichmentPipeline(use_mocks=True)
    scorer = RiskScorer()

    # Convert to list of dicts
    companies = df.to_dict("records")

    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current, total):
        progress = current / total
        progress_bar.progress(progress)
        status_text.text(f"Processing {current}/{total} companies...")

    # Enrich companies
    enriched = pipeline.enrich_to_dicts(
        companies,
        name_column=name_col,
        jurisdiction_column=jur_col,
        flatten=True,
        progress_callback=update_progress,
    )

    # Score companies
    scored = scorer.score_companies(enriched)

    status_text.text("Analysis complete!")

    # Create results DataFrame
    results_df = pd.DataFrame(scored)

    # Store in session state
    st.session_state["analysis_results"] = results_df

    # Display results
    display_results(results_df)


def display_results(df: pd.DataFrame):
    """Display analysis results."""
    st.markdown("---")
    st.markdown("### 📊 Analysis Results")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Companies", len(df))

    with col2:
        high_risk = len(df[df["risk_level"] == "High Risk"])
        st.metric("High Risk", high_risk, delta=None)

    with col3:
        medium_risk = len(df[df["risk_level"] == "Medium Risk"])
        st.metric("Medium Risk", medium_risk)

    with col4:
        low_risk = len(df[df["risk_level"] == "Low Risk"])
        st.metric("Low Risk", low_risk)

    # Risk distribution chart
    if len(df) > 1:
        st.plotly_chart(create_risk_distribution(df), use_container_width=True)

    # Results table
    st.markdown("### Detailed Results")

    # Display columns
    display_cols = [
        "company_name",
        "risk_score",
        "risk_level",
        "jurisdiction",
        "status",
        "officer_count",
        "online_hit_count",
    ]
    available_cols = [c for c in display_cols if c in df.columns]

    # Sort by risk score
    sorted_df = df.sort_values("risk_score", ascending=True)

    # Color-code risk levels
    def highlight_risk(row):
        if row["risk_level"] == "High Risk":
            return ["background-color: #ffcccb"] * len(row)
        elif row["risk_level"] == "Medium Risk":
            return ["background-color: #ffffcc"] * len(row)
        else:
            return ["background-color: #ccffcc"] * len(row)

    styled_df = sorted_df[available_cols].style.apply(highlight_risk, axis=1)
    st.dataframe(styled_df, use_container_width=True, height=400)

    # Risk flags summary
    st.markdown("### ⚠️ Risk Flags Summary")
    all_flags = []
    for flags in df["risk_flags"]:
        if isinstance(flags, list):
            all_flags.extend(flags)

    if all_flags:
        flag_counts = pd.Series(all_flags).value_counts()
        for flag, count in flag_counts.items():
            st.markdown(f"- **{flag}**: {count} companies")
    else:
        st.info("No risk flags identified")

    # Individual company details
    st.markdown("### 🔎 Company Details")
    selected_company = st.selectbox(
        "Select a company to view details",
        options=df["company_name"].tolist(),
    )

    if selected_company:
        company_data = df[df["company_name"] == selected_company].iloc[0].to_dict()

        col1, col2 = st.columns([1, 2])

        with col1:
            st.plotly_chart(
                create_risk_gauge(company_data.get("risk_score", 0)),
                use_container_width=True,
            )

        with col2:
            st.plotly_chart(
                create_category_breakdown(company_data),
                use_container_width=True,
            )

        # Company details
        st.markdown("**Company Information:**")
        info_cols = st.columns(3)
        with info_cols[0]:
            st.markdown(f"- **Jurisdiction:** {company_data.get('jurisdiction', 'N/A')}")
            st.markdown(f"- **Status:** {company_data.get('status', 'N/A')}")
        with info_cols[1]:
            st.markdown(f"- **Officers:** {company_data.get('officer_count', 'N/A')}")
            st.markdown(f"- **Lifespan:** {company_data.get('lifespan_days', 'N/A')} days")
        with info_cols[2]:
            st.markdown(f"- **Online Hits:** {company_data.get('online_hit_count', 'N/A')}")
            st.markdown(f"- **Has Wikipedia:** {company_data.get('has_wikipedia', 'N/A')}")

        flags = company_data.get("risk_flags", [])
        if flags:
            st.warning(f"**Risk Flags:** {', '.join(flags)}")

    # Export section
    st.markdown("---")
    st.markdown("### 💾 Export Results")

    col1, col2 = st.columns(2)

    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="company_analysis_results.csv",
            mime="text/csv",
        )

    with col2:
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button(
            label="Download Excel",
            data=buffer.getvalue(),
            file_name="company_analysis_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def fraud_database_page():
    """Render the fraud database browser page."""
    st.title("Fraud Cases Database")

    fraud_df = load_fraud_dataset()

    if fraud_df is None:
        st.warning(
            "Fraud dataset not found. Run `python compile_dataset.py` to generate it."
        )

        if st.button("Generate Dataset Now"):
            with st.spinner("Generating dataset..."):
                from scrapers.data_compiler import DataCompiler

                compiler = DataCompiler()
                fraud_df = compiler.save_dataset(
                    filepath="data/fraudulent_companies.csv",
                    include_scraped=True,
                    include_synthetic=True,
                    synthetic_count=60,
                )
                st.success(f"Generated {len(fraud_df)} fraud cases!")
                st.rerun()
        return

    # Filters
    st.markdown("### Filters")
    col1, col2, col3 = st.columns(3)

    with col1:
        fraud_types = ["All"] + fraud_df["fraud_type"].unique().tolist()
        selected_type = st.selectbox("Fraud Type", fraud_types)

    with col2:
        sources = ["All"] + fraud_df["source"].unique().tolist()
        selected_source = st.selectbox("Source", sources)

    with col3:
        show_synthetic = st.checkbox("Include Synthetic Cases", value=True)

    # Apply filters
    filtered_df = fraud_df.copy()

    if selected_type != "All":
        filtered_df = filtered_df[filtered_df["fraud_type"] == selected_type]

    if selected_source != "All":
        filtered_df = filtered_df[filtered_df["source"] == selected_source]

    if not show_synthetic:
        filtered_df = filtered_df[~filtered_df["is_synthetic"]]

    # Stats
    st.markdown("### Dataset Statistics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Cases", len(filtered_df))
    with col2:
        real = len(filtered_df[~filtered_df["is_synthetic"]])
        st.metric("Real Cases", real)
    with col3:
        synthetic = len(filtered_df[filtered_df["is_synthetic"]])
        st.metric("Synthetic Cases", synthetic)
    with col4:
        jurisdictions = filtered_df["jurisdiction"].nunique()
        st.metric("Jurisdictions", jurisdictions)

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        type_counts = filtered_df["fraud_type"].value_counts()
        fig = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title="Fraud Types Distribution",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        jur_counts = filtered_df["jurisdiction"].value_counts().head(10)
        fig = px.bar(
            x=jur_counts.index,
            y=jur_counts.values,
            title="Top Jurisdictions",
            labels={"x": "Jurisdiction", "y": "Count"},
        )
        st.plotly_chart(fig, use_container_width=True)

    # Data table
    st.markdown("### Cases")

    display_cols = [
        "company_name",
        "fraud_type",
        "jurisdiction",
        "case_date",
        "penalty_amount",
        "source",
        "is_synthetic",
    ]

    st.dataframe(
        filtered_df[display_cols].sort_values("case_date", ascending=False),
        use_container_width=True,
        height=400,
    )

    # Case details
    st.markdown("### Case Details")
    selected_case = st.selectbox(
        "Select a case to view details",
        options=filtered_df["company_name"].tolist(),
    )

    if selected_case:
        case = filtered_df[filtered_df["company_name"] == selected_case].iloc[0]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Company:** {case['company_name']}")
            st.markdown(f"**Fraud Type:** {case['fraud_type']}")
            st.markdown(f"**Jurisdiction:** {case['jurisdiction']}")
            st.markdown(f"**Case Date:** {case['case_date']}")

        with col2:
            penalty = case["penalty_amount"]
            if pd.notna(penalty):
                st.markdown(f"**Penalty:** ${penalty:,.0f}")
            else:
                st.markdown("**Penalty:** N/A")
            st.markdown(f"**Source:** {case['source']}")
            st.markdown(f"**Synthetic:** {'Yes' if case['is_synthetic'] else 'No'}")

        st.markdown("**Description:**")
        st.info(case["description"])


def sanctions_screening_page():
    """Render the sanctions screening page."""
    st.title("Sanctions Screening")
    st.markdown("### Screen companies against OFAC sanctions lists")

    # Load OFAC names
    ofac_names = load_ofac_names()

    if not ofac_names:
        st.warning(
            """
            OFAC names list not found. Please run the data download first:
            ```bash
            python combine_all_sources.py
            ```
            Or download directly:
            ```python
            from scrapers.opensanctions import OpenSanctionsClient
            client = OpenSanctionsClient()
            client.download_names_list()
            ```
            """
        )

        if st.button("Download OFAC Data Now"):
            with st.spinner("Downloading OFAC data..."):
                try:
                    from scrapers.opensanctions import OpenSanctionsClient
                    client = OpenSanctionsClient()
                    filepath = client.download_names_list()
                    if filepath:
                        st.success(f"Downloaded OFAC data!")
                        st.rerun()
                    else:
                        st.error("Download failed")
                except Exception as e:
                    st.error(f"Error: {e}")
        return

    st.success(f"✅ OFAC database loaded: {len(ofac_names):,} sanctioned names")

    # Single company screening
    st.markdown("### Quick Screen")
    company_input = st.text_input(
        "Enter company name to screen",
        placeholder="e.g., Global Trading LLC"
    )

    if company_input:
        company_lower = company_input.lower().strip()

        # Check for exact match
        if company_lower in ofac_names:
            st.error(f"⚠️ **EXACT MATCH FOUND** - '{company_input}' is on the OFAC sanctions list!")
        else:
            # Check for partial matches
            partial_matches = []
            for name in ofac_names:
                if company_lower in name or name in company_lower:
                    partial_matches.append(name)

            if partial_matches:
                st.warning(f"⚠️ **PARTIAL MATCHES FOUND** - {len(partial_matches)} potential matches")
                with st.expander("View matches"):
                    for match in partial_matches[:20]:
                        st.markdown(f"- {match}")
                    if len(partial_matches) > 20:
                        st.markdown(f"... and {len(partial_matches) - 20} more")
            else:
                st.success(f"✅ No sanctions matches found for '{company_input}'")

    # Batch screening
    st.markdown("---")
    st.markdown("### Batch Screening")
    st.markdown("Upload a file with company names to screen against OFAC list")

    uploaded_file = st.file_uploader(
        "Upload Excel or CSV",
        type=["xlsx", "xls", "csv"],
        key="sanctions_upload"
    )

    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            name_col = st.selectbox(
                "Select company name column",
                options=df.columns.tolist(),
                key="sanctions_name_col"
            )

            if st.button("Screen All Companies", type="primary"):
                results = []
                progress = st.progress(0)

                for i, row in df.iterrows():
                    company_name = str(row[name_col]).strip()
                    company_lower = company_name.lower()

                    # Check matches
                    exact_match = company_lower in ofac_names
                    partial_matches = [n for n in ofac_names if company_lower in n or n in company_lower]

                    if exact_match:
                        status = "EXACT MATCH"
                        match_count = 1
                    elif partial_matches:
                        status = "PARTIAL MATCH"
                        match_count = len(partial_matches)
                    else:
                        status = "CLEAR"
                        match_count = 0

                    results.append({
                        'company_name': company_name,
                        'status': status,
                        'match_count': match_count,
                        'matches': '; '.join(partial_matches[:5]) if partial_matches else ''
                    })

                    progress.progress((i + 1) / len(df))

                results_df = pd.DataFrame(results)

                # Summary
                st.markdown("### Screening Results")
                col1, col2, col3 = st.columns(3)
                with col1:
                    exact_count = len(results_df[results_df['status'] == 'EXACT MATCH'])
                    st.metric("Exact Matches", exact_count, delta=None)
                with col2:
                    partial_count = len(results_df[results_df['status'] == 'PARTIAL MATCH'])
                    st.metric("Partial Matches", partial_count)
                with col3:
                    clear_count = len(results_df[results_df['status'] == 'CLEAR'])
                    st.metric("Clear", clear_count)

                # Color-code results
                def highlight_status(row):
                    if row['status'] == 'EXACT MATCH':
                        return ['background-color: #ff6b6b'] * len(row)
                    elif row['status'] == 'PARTIAL MATCH':
                        return ['background-color: #ffd93d'] * len(row)
                    else:
                        return ['background-color: #6bcb77'] * len(row)

                st.dataframe(
                    results_df.style.apply(highlight_status, axis=1),
                    use_container_width=True,
                    height=400
                )

                # Export
                csv = results_df.to_csv(index=False)
                st.download_button(
                    "Download Results CSV",
                    data=csv,
                    file_name="sanctions_screening_results.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"Error processing file: {e}")

    # Info about OFAC
    st.markdown("---")
    st.markdown("### About OFAC Sanctions")
    st.markdown(
        """
    The **Office of Foreign Assets Control (OFAC)** administers and enforces
    economic and trade sanctions based on US foreign policy and national security goals.

    **Data Source:** [OpenSanctions](https://www.opensanctions.org/datasets/us_ofac_press_releases/)

    **Disclaimer:** This screening is for informational purposes only.
    Always verify matches through official OFAC sources before making
    compliance decisions.
    """
    )


def data_management_page():
    """Render the data management page."""
    st.title("Data Management")
    st.markdown("### Manage and update data sources")

    # Current database status
    st.markdown("### Current Database")
    fraud_df = load_fraud_dataset()

    if fraud_df is not None:
        st.success(f"Database loaded: {len(fraud_df):,} records")

        # Show source breakdown
        source_counts = fraud_df['source'].value_counts()
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Records by Source:**")
            for source, count in source_counts.items():
                st.markdown(f"- {source}: {count:,}")

        with col2:
            st.markdown("**Records by Type (Top 5):**")
            type_counts = fraud_df['fraud_type'].value_counts().head(5)
            for ftype, count in type_counts.items():
                st.markdown(f"- {ftype}: {count:,}")
    else:
        st.warning("No database found")

    st.markdown("---")

    # Actions
    st.markdown("### Update Data")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Extract from PDFs**")
        st.markdown("Process SEC complaint PDFs and add to database")
        if st.button("Extract PDFs", key="extract_pdfs"):
            with st.spinner("Extracting from PDFs..."):
                try:
                    from scrapers.pdf_extractor import extract_all_pdfs
                    from combine_all_sources import combine_sources
                    result = combine_sources(extract_pdfs=True, download_ofac=False)
                    st.success("PDF extraction complete!")
                    if result.get("success"):
                        st.code(result.get("output", "Done"))
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    with col2:
        st.markdown("**Download OpenSanctions**")
        st.markdown("Download latest OFAC sanctions data")
        if st.button("Download OFAC", key="download_ofac"):
            with st.spinner("Downloading OFAC data..."):
                try:
                    from scrapers.opensanctions import OpenSanctionsClient
                    client = OpenSanctionsClient()
                    filepath = client.download_dataset('ofac_press_releases', force=True)
                    if filepath:
                        st.success(f"Downloaded to {filepath}")
                        # Also download names list
                        names_path = client.download_names_list()
                        if names_path:
                            st.success(f"Names list: {names_path}")
                    else:
                        st.error("Download failed")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("---")

    # Combine all sources
    st.markdown("### Combine All Sources")
    st.markdown(
        """
        Run the full data combination script to:
        - Extract from all SEC complaint PDFs
        - Download OpenSanctions OFAC data
        - Include known SEC enforcement cases
        - Deduplicate and merge into unified database
        """
    )

    if st.button("Combine All Sources", type="primary"):
        with st.spinner("Combining all data sources... This may take a few minutes."):
            try:
                from combine_all_sources import combine_sources
                result = combine_sources(extract_pdfs=True, download_ofac=True)
                st.success("Data combination complete!")
                if result.get("success"):
                    st.code(result.get("output", "Done")[-3000:] if result.get("output") else "Done")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # PDF inventory
    st.markdown("---")
    st.markdown("### PDF Inventory")

    pdf_dirs = ['data/pdfs', 'data/pdfs/2025', 'data']
    total_pdfs = 0
    for dir_path in pdf_dirs:
        full_path = os.path.join(os.path.dirname(__file__), dir_path)
        if os.path.exists(full_path):
            pdfs = [f for f in os.listdir(full_path) if f.endswith('.pdf')]
            if pdfs:
                st.markdown(f"**{dir_path}:** {len(pdfs)} PDFs")
                total_pdfs += len(pdfs)

    st.metric("Total PDFs Available", total_pdfs)


def network_viz_page():
    """Render the network visualization demo page."""
    st.title("Network Investigation Demo")
    st.markdown("### Interactive Fraud Network Visualization")

    st.markdown(
        """
    This demo shows interconnected relationships in major crypto fraud cases.
    The network reveals how entities, people, addresses, and legal cases are linked.
    """
    )

    # Load demo data
    try:
        network_data = load_demo_network()
    except FileNotFoundError:
        st.error("Demo network data not found. Check data/examples/fraud_network_demo.json")
        return

    # Sidebar controls
    st.sidebar.markdown("### Network Controls")

    # Cluster selection
    clusters = network_data.get("clusters", [])
    cluster_options = ["Full Network"] + [c["label"] for c in clusters]
    selected_cluster = st.sidebar.selectbox("Focus Cluster", cluster_options)

    # Node type filter
    all_types = list(set(n["type"] for n in network_data["nodes"]))
    selected_types = st.sidebar.multiselect(
        "Node Types",
        options=all_types,
        default=all_types,
        help="Filter by entity type"
    )

    # Entity focus
    all_entities = [n["label"] for n in network_data["nodes"]]
    focus_entity = st.sidebar.selectbox(
        "Focus Entity (optional)",
        options=["None"] + all_entities,
        help="Show only entities connected to this one"
    )

    depth = st.sidebar.slider("Connection Depth", 1, 3, 2)

    # Apply filters
    filtered_data = network_data

    if selected_cluster != "Full Network":
        cluster_id = next(
            (c["id"] for c in clusters if c["label"] == selected_cluster),
            None
        )
        if cluster_id:
            filtered_data = create_cluster_subgraph(network_data, cluster_id)

    if selected_types and set(selected_types) != set(all_types):
        filtered_data = filter_by_node_type(filtered_data, selected_types)

    if focus_entity != "None":
        entity_id = next(
            (n["id"] for n in network_data["nodes"] if n["label"] == focus_entity),
            None
        )
        if entity_id:
            filtered_data = get_connected_entities(network_data, entity_id, depth)

    # Display stats
    st.markdown("### Network Statistics")
    col1, col2, col3, col4 = st.columns(4)

    stats = network_data.get("statistics", {})
    with col1:
        st.metric("Companies", stats.get("companies", 0))
    with col2:
        st.metric("Persons", stats.get("persons", 0))
    with col3:
        st.metric("Addresses", stats.get("addresses", 0))
    with col4:
        st.metric("Legal Cases", stats.get("cases", 0))

    # Compute metrics
    metrics = compute_network_metrics(filtered_data)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Visible Nodes", metrics["node_count"])
    with col2:
        st.metric("Connections", metrics["edge_count"])
    with col3:
        density = metrics.get("density", 0) * 100
        st.metric("Network Density", f"{density:.1f}%")

    # Key findings
    if "top_connected" in metrics and metrics["top_connected"]:
        st.markdown("### Key Findings")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Most Connected Entities:**")
            for entity_id, centrality in metrics["top_connected"][:5]:
                node = next(
                    (n for n in network_data["nodes"] if n["id"] == entity_id),
                    None
                )
                if node:
                    st.markdown(f"- {node['label']} ({centrality:.2%})")

        with col2:
            if "key_bridges" in metrics and metrics["key_bridges"]:
                st.markdown("**Key Bridge Entities:**")
                for entity_id, centrality in metrics["key_bridges"][:5]:
                    node = next(
                        (n for n in network_data["nodes"] if n["id"] == entity_id),
                        None
                    )
                    if node:
                        st.markdown(f"- {node['label']} ({centrality:.2%})")

    # Generate network visualization
    st.markdown("### Interactive Network Graph")
    st.markdown(
        """
    **Legend:**
    - Red boxes = Companies (colored by risk)
    - Blue circles = People
    - Green triangles = Addresses
    - Purple diamonds = Legal Cases

    **Interactions:** Drag nodes, zoom with scroll, click for details
    """
    )

    # Create pyvis network
    try:
        import tempfile
        import streamlit.components.v1 as components

        net = create_pyvis_network(
            filtered_data,
            height="600px",
            width="100%",
            bgcolor="#0e1117",
            font_color="#fafafa",
        )

        # Save to temp file and display
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w") as f:
            net.save_graph(f.name)
            with open(f.name, "r") as html_file:
                html_content = html_file.read()
            components.html(html_content, height=620, scrolling=True)

    except ImportError as e:
        st.error(f"Missing dependency: {e}. Run: pip install pyvis networkx")
    except Exception as e:
        st.error(f"Error rendering network: {e}")

    # Cluster overview
    st.markdown("---")
    st.markdown("### Fraud Clusters Overview")

    for cluster in clusters:
        with st.expander(f"{cluster['label']} ({len(cluster['entities'])} entities)"):
            entity_names = []
            for eid in cluster["entities"]:
                node = next(
                    (n for n in network_data["nodes"] if n["id"] == eid),
                    None
                )
                if node:
                    entity_names.append(f"- **{node['label']}** ({node['type']})")
            st.markdown("\n".join(entity_names))

    # Entity details table
    st.markdown("---")
    st.markdown("### Entity Details")

    entity_type_filter = st.selectbox(
        "Filter by Type",
        options=["All"] + all_types
    )

    nodes_to_show = network_data["nodes"]
    if entity_type_filter != "All":
        nodes_to_show = [n for n in nodes_to_show if n["type"] == entity_type_filter]

    # Build dataframe
    entity_df = pd.DataFrame([
        {
            "Name": n["label"],
            "Type": n["type"].title(),
            "Status": n.get("status", "N/A"),
            "Jurisdiction": n.get("jurisdiction", "N/A"),
            "Risk Score": n.get("risk_score", "N/A"),
            "Description": n.get("description", "")[:80] + "..." if len(n.get("description", "")) > 80 else n.get("description", ""),
        }
        for n in nodes_to_show
    ])

    st.dataframe(entity_df, use_container_width=True, height=300)

    # Total penalty
    total_penalty = stats.get("total_penalty_amount", 0)
    if total_penalty:
        st.markdown(f"**Total Penalties in Network:** ${total_penalty:,.0f}")


def settings_page():
    """Render the settings page."""
    st.title("Settings")

    st.markdown("### API Configuration")
    st.markdown(
        """
    Configure your API keys to enable real data enrichment.
    Without API keys, the tool will use mock data for demonstration.

    **Environment Variables:**
    - `BRAVE_API_KEY` - Brave Search API token
    - `OPENCORPORATES_API_TOKEN` - OpenCorporates API token

    You can set these in a `.env` file in the project root:
    ```
    BRAVE_API_KEY=your_key_here
    OPENCORPORATES_API_TOKEN=your_token_here
    ```
    """
    )

    st.markdown("### Current Configuration")

    if BRAVE_API_KEY:
        st.success(f"✅ Brave Search API: Configured (key: {BRAVE_API_KEY[:8]}...)")
    else:
        st.error("❌ Brave Search API: Not configured")
        st.markdown(
            """
        **Get a Brave Search API key:**
        1. Visit [Brave Search API](https://api-dashboard.search.brave.com)
        2. Sign up for a free account
        3. Create an API key
        4. Free tier: 2,000 queries/month
        """
        )

    if OPENCORPORATES_API_TOKEN:
        st.success(
            f"✅ OpenCorporates API: Configured (token: {OPENCORPORATES_API_TOKEN[:8]}...)"
        )
    else:
        st.error("❌ OpenCorporates API: Not configured")
        st.markdown(
            """
        **Get an OpenCorporates API token:**
        1. Visit [OpenCorporates](https://opencorporates.com)
        2. Sign up for an account
        3. Request API access
        4. Free tier: 200 requests/month
        """
        )

    st.markdown("### Rate Limiting")
    st.markdown(
        """
    The tool includes built-in rate limiting to avoid API bans:
    - Default delay: 2 seconds between requests
    - Configurable via `RATE_LIMIT_DELAY` environment variable
    """
    )

    st.markdown("---")
    st.markdown("### Data Sources")
    st.markdown(
        """
    **Built-in Data Sources:**
    - SEC EDGAR filings
    - SEC Enforcement Actions
    - SEC Complaint PDFs (29+ cases)
    - OpenSanctions OFAC Press Releases

    **External APIs:**
    - Brave Search API - Web presence verification
    - OpenCorporates API - Corporate registry data
    """
    )


def main():
    """Main application entry point."""
    # Sidebar navigation
    st.sidebar.title("Navigation")

    pages = {
        "Home": home_page,
        "Upload & Analyze": upload_analyze_page,
        "Sanctions Screening": sanctions_screening_page,
        "Fraud Database": fraud_database_page,
        "Network Investigation": network_viz_page,
        "Data Management": data_management_page,
        "Settings": settings_page,
    }

    selection = st.sidebar.radio("Go to", list(pages.keys()))

    # Render selected page
    pages[selection]()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
    **Company Research Tool**
    KYC & Fraud Investigation Platform

    **Data Sources:**
    - SEC Enforcement
    - OpenSanctions OFAC
    - Brave Search API
    - OpenCorporates API
    """
    )


if __name__ == "__main__":
    main()
