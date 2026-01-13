# Company Research Tool - Improvement Analysis

## Initial Assessment Notes

### Project Overview
**Company Research Tool** is a Streamlit web application for investigating companies for:
- Shell company detection
- Fraud risk assessment
- Corporate legitimacy evaluation

### Current Architecture

```
company-research-tool/
├── app.py                      # Main Streamlit application (4 pages)
├── config.py                   # Configuration and environment settings
├── compile_dataset.py          # Dataset generation script
├── requirements.txt            # Python dependencies
│
├── scrapers/
│   ├── sec_scraper.py          # SEC enforcement case scraper
│   ├── data_compiler.py        # Dataset compilation (real + synthetic)
│   └── pdf_extractor.py        # PDF text extraction and parsing
│
├── enrichment/
│   ├── brave_search.py         # Brave Search API client
│   ├── opencorporates.py       # OpenCorporates API client
│   └── enrichment_pipeline.py  # Multi-source data orchestration
│
├── scoring/
│   └── risk_scorer.py          # Weighted risk scoring engine (0-4 GPA scale)
│
├── utils/
│   └── helpers.py              # Common utilities
│
└── data/
    ├── fraudulent_companies.csv  # Compiled fraud database (400+ cases)
    ├── sample_input.xlsx         # Sample upload file
    └── pdfs/                     # Downloaded SEC complaint PDFs
```

### Key Components

1. **Web Application (app.py)** - Streamlit UI with 4 pages:
   - Home: Dashboard with database statistics and API status
   - Upload & Analyze: File upload, column mapping, batch enrichment
   - Fraud Database: Searchable/filterable view of known fraud cases
   - Settings: API configuration guidance

2. **Enrichment Pipeline** - Fetches data from:
   - Brave Search API (online presence, social media, Wikipedia, regulatory mentions)
   - OpenCorporates API (corporate registry, officers, status, jurisdiction)

3. **Risk Scorer** - Weighted scoring engine (0-4 GPA scale):
   - Online Activity (30%): Hit count, social media, Wikipedia
   - Corporate Info (25%): Status, lifespan, registered address
   - Officers & Structure (20%): Officer count, address matching
   - Jurisdiction Risk (15%): High-risk offshore locations
   - External Factors (10%): Regulatory mentions, data confidence

4. **PDF Extractor** - Extracts entities from SEC complaint PDFs:
   - Companies with jurisdictions and identifiers
   - Individuals with CRD numbers
   - Fraud types, amounts, victim counts

5. **Fraud Database** - 400+ cases:
   - Real cases extracted from SEC enforcement actions
   - Synthetic shell company profiles for training/demo

### Current Limitations Identified

- **No single-company lookup** - Must upload a file even for one company
- **Sequential API calls** - Batch processing is slow (O(N) with rate limits)
- **No caching** - Same company re-fetched every time, wasting API quota
- **No retry logic** - Transient failures break entire batch
- **No persistence** - Results lost on page refresh
- **Fixed scoring weights** - Not customizable for different use cases
- **No tests** - Hard to refactor with confidence

---

## 30 Ideas for Improvement

### Robustness & Reliability
1. **Add async/concurrent API fetching** - Parallelize requests for dramatic speedup
2. **Implement retry logic with exponential backoff** - Handle transient failures gracefully
3. **Add circuit breaker pattern** - Prevent cascading failures when APIs are down
4. **Implement request/response caching layer** - Avoid re-fetching same company data
5. **Add input validation and sanitization** - Prevent weird errors from bad input
6. **Create custom exception hierarchy** - Better error handling and debugging
7. **Add structured logging throughout** - Enable debugging and monitoring
8. **Create comprehensive pytest test suite** - Enable confident refactoring

### Performance
9. **Add database persistence (SQLite/PostgreSQL)** - Store results, enable history
10. **Implement Streamlit caching decorators** - `@st.cache_data` for expensive operations
11. **Batch API requests where possible** - Reduce overhead
12. **Add pagination for large uploads** - Handle 1000+ company batches
13. **Implement background task processing** - Don't block UI during long operations

### User Experience
14. **Add single-company quick lookup mode** - Text input → instant results
15. **Add real-time progress streaming with ETA** - Show expected completion time
16. **Add company comparison view** - Side-by-side analysis of two companies
17. **Add historical tracking of risk profiles** - How has this company changed over time?
18. **Add network graph for company relationships** - Visualize shared officers/addresses
19. **Add formatted export templates/reports** - PDF/Word for compliance teams
20. **Enhance fraud database with advanced filtering** - Multiple filter criteria
21. **Add dark mode toggle** - User preference for visual comfort

### Features & Usefulness
22. **Integrate OFAC/sanctions list screening** - Check against government watchlists
23. **Add beneficial ownership tracking** - Who really owns this company?
24. **Add news sentiment analysis** - Analyze regulatory/fraud mention sentiment
25. **Implement ML-based risk prediction** - Train model on fraud cases
26. **Add company relationship mapping** - Discover hidden connections
27. **Add adverse media monitoring** - Alert on negative news
28. **Add confidence intervals to risk scores** - Quantify uncertainty
29. **Add configurable scoring weights via UI** - Customize for industry/use case
30. **Create REST API endpoint** - Programmatic access via FastAPI

---

## Deep Evaluation of Top Candidates

### Idea #14: Single-Company Quick Lookup
- **Current problem**: Users MUST upload a file even to check ONE company. Major UX friction.
- **Implementation**: Text input → call existing pipeline → display results inline
- **Complexity**: Low (reuse existing code)
- **Impact**: Transforms usability for ad-hoc investigations

### Idea #4: Request Caching Layer
- **Current problem**: Same company re-fetched every time, wasting expensive API quota
- **Implementation**: `@st.cache_data` + optional SQLite for persistence
- **Complexity**: Medium
- **Impact**: Massive for API quota management and perceived speed

### Idea #1: Concurrent Enrichment
- **Current problem**: Sequential 2s delays × 2 APIs × N companies = O(N) wait time
- **Implementation**: `concurrent.futures.ThreadPoolExecutor` or asyncio
- **Complexity**: Medium
- **Impact**: 5-10x speedup for batch processing

### Idea #2: Retry Logic with Backoff
- **Current problem**: Single transient failure kills the entire batch
- **Implementation**: Use `tenacity` library with exponential backoff
- **Complexity**: Low
- **Impact**: Essential reliability under flaky conditions

### Idea #29: Configurable Scoring Weights
- **Current problem**: Fixed weights don't suit all industries/use cases
- **Implementation**: Sliders in Settings → pass custom weights to scorer
- **Complexity**: Low-Medium
- **Impact**: Customization for diverse professional contexts

### Idea #8: Test Suite
- **Complexity**: High (comprehensive coverage)
- **Impact**: Developer confidence, but not user-visible

### Idea #9: Database Persistence
- **Complexity**: High (architectural change)
- **Impact**: Good for power users, but demo focus suggests overkill

### Idea #15: Progress with ETA
- **Current problem**: Progress bar shows % but not expected wait time
- **Implementation**: Track timing, estimate remaining
- **Complexity**: Low-Medium
- **Impact**: Reduces perceived wait anxiety

---

## Final Top 5 Ideas (Best to Good)

After careful evaluation based on **obvious accretiveness** and **pragmatism**:

---

### 🥇 #1: Single-Company Quick Lookup Mode

**What it is**: Add a text input on the Home page or a dedicated "Quick Check" page where users can type a company name and immediately see risk assessment results—no file upload required.

**Why it's the best idea**:
- **Massive UX improvement**: The current flow forces users to create an Excel/CSV file even to check ONE company. For investigators doing ad-hoc lookups during calls or meetings, this is a dealbreaker. Most usage will be "Is this company sketchy?" not "Here's my batch of 50."
- **Zero architectural changes**: The `EnrichmentPipeline` and `RiskScorer` already work on single companies. We're just adding a new entry point.
- **Immediately obvious value**: Any user will see "Quick Check" and understand it. No explanation needed.

**Implementation approach** (~50 lines of Streamlit code):

```python
def quick_check_page():
    st.title("🔎 Quick Company Check")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        company_name = st.text_input(
            "Company Name",
            placeholder="Enter company name to analyze..."
        )
    with col2:
        jurisdiction = st.selectbox(
            "Jurisdiction (optional)",
            ["Auto-detect", "us_de", "us_ca", "gb", "sg", "ky", "vg", "pa"]
        )
    
    if st.button("🔍 Analyze", type="primary") and company_name:
        with st.spinner(f"Analyzing {company_name}..."):
            pipeline = EnrichmentPipeline(use_mocks=True)
            scorer = RiskScorer()
            
            jur = None if jurisdiction == "Auto-detect" else jurisdiction
            enriched = pipeline.enrich_company(company_name, jur)
            scored = scorer.calculate_score(enriched.to_flat_dict())
            
            # Display results using existing visualization functions
            col1, col2 = st.columns([1, 2])
            with col1:
                st.plotly_chart(create_risk_gauge(scored.total_score))
            with col2:
                st.plotly_chart(create_category_breakdown({...}))
            
            # Show risk flags
            if scored.flags:
                st.warning(f"⚠️ Risk Flags: {', '.join(scored.flags)}")
```

**How users will perceive it**: "Finally! I can just type a name and get an answer." This removes the single biggest friction point in the current design.

**Confidence**: 95% certain this is the highest-impact improvement possible.

---

### 🥈 #2: Smart Caching Layer for Enrichment Results

**What it is**: Cache API responses so the same company isn't re-fetched within a configurable window (e.g., 24 hours). Use Streamlit's `@st.cache_data` for in-session caching and optionally a SQLite database for persistent caching.

**Why it's essential**:
- **API quotas are precious**: Brave Search free tier = 2,000 queries/month. OpenCorporates = 200/month. Without caching, a single page refresh or re-run burns queries.
- **Perceived performance**: Cached responses return instantly. Users feel the tool is "fast."
- **Idempotent behavior**: Refreshing the page shouldn't change results (unless cache is stale).

**Implementation approach**:

For Streamlit session caching:
```python
@st.cache_data(ttl=86400)  # 24-hour TTL
def cached_enrich_company(company_name: str, jurisdiction: str | None) -> dict:
    pipeline = EnrichmentPipeline(use_mocks=True)
    return pipeline.enrich_company(company_name, jurisdiction).to_dict()
```

For persistent SQLite caching:
```python
import sqlite3
import json
from datetime import datetime, timedelta

class EnrichmentCache:
    def __init__(self, db_path: str = "data/cache.db", ttl_hours: int = 24):
        self.conn = sqlite3.connect(db_path)
        self.ttl = timedelta(hours=ttl_hours)
        self._init_table()
    
    def _init_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS enrichment_cache (
                company_key TEXT PRIMARY KEY,
                data JSON NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def get(self, company_name: str, jurisdiction: str | None) -> dict | None:
        key = f"{company_name.lower()}:{jurisdiction or 'any'}"
        cursor = self.conn.execute(
            "SELECT data, fetched_at FROM enrichment_cache WHERE company_key = ?",
            (key,)
        )
        row = cursor.fetchone()
        if row:
            fetched_at = datetime.fromisoformat(row[1])
            if datetime.now() - fetched_at < self.ttl:
                return json.loads(row[0])
        return None
    
    def set(self, company_name: str, jurisdiction: str | None, data: dict):
        key = f"{company_name.lower()}:{jurisdiction or 'any'}"
        self.conn.execute(
            "INSERT OR REPLACE INTO enrichment_cache (company_key, data) VALUES (?, ?)",
            (key, json.dumps(data))
        )
        self.conn.commit()
```

**How users will perceive it**: "It remembered! I don't have to wait again." Subtle but critical for professional use.

**Confidence**: 90% certain this should be in the top 2.

---

### 🥉 #3: Concurrent Enrichment with Progress Streaming

**What it is**: Parallelize API calls during batch enrichment so N companies take O(1) time instead of O(N). Show real-time progress with estimated completion time.

**Why it matters**:
- **Current bottleneck**: 2-second rate limit × 2 APIs × 20 companies = 80 seconds minimum. With concurrency, this drops to ~4 seconds (limited by rate limits per API, not serialization).
- **Professional credibility**: Fast tools feel professional. Slow tools feel like demos.
- **Progress streaming**: Users waiting 80 seconds with only a progress bar feel anxious. Showing "~45 seconds remaining" and streaming individual company results as they complete is vastly better.

**Implementation approach**:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterator
import time

class ConcurrentEnrichmentPipeline(EnrichmentPipeline):
    def enrich_concurrent(
        self,
        companies: list[dict],
        name_column: str = "Company Name",
        jurisdiction_column: str | None = None,
        max_workers: int = 5,
    ) -> Iterator[tuple[int, EnrichedCompany]]:
        """Enrich companies concurrently, yielding results as they complete."""
        
        def enrich_one(idx: int, company: dict) -> tuple[int, EnrichedCompany]:
            name = company.get(name_column, "")
            jur = company.get(jurisdiction_column) if jurisdiction_column else None
            return idx, self.enrich_company(name, jur)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(enrich_one, i, c): i
                for i, c in enumerate(companies)
            }
            for future in as_completed(futures):
                yield future.result()
```

For Streamlit with progress and ETA:
```python
def analyze_companies_concurrent(df: pd.DataFrame, name_col: str, jur_col: str | None):
    pipeline = ConcurrentEnrichmentPipeline(use_mocks=True)
    scorer = RiskScorer()
    
    companies = df.to_dict("records")
    total = len(companies)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.empty()
    
    results = [None] * total
    start_time = time.time()
    completed = 0
    
    for idx, enriched in pipeline.enrich_concurrent(companies, name_col, jur_col):
        results[idx] = enriched
        completed += 1
        
        # Calculate ETA
        elapsed = time.time() - start_time
        rate = completed / elapsed if elapsed > 0 else 0
        remaining = (total - completed) / rate if rate > 0 else 0
        
        progress_bar.progress(completed / total)
        status_text.text(f"Processing {completed}/{total} • ~{remaining:.0f}s remaining")
        
        # Stream partial results
        completed_results = [r for r in results if r is not None]
        if len(completed_results) % 5 == 0:  # Update every 5 completions
            results_container.dataframe(pd.DataFrame([r.to_flat_dict() for r in completed_results]))
    
    status_text.text(f"✅ Completed {total} companies in {elapsed:.1f}s")
    return results
```

**How users will perceive it**: "Wow, that was fast!" Transforms batch analysis from "coffee break" to "quick task."

**Confidence**: 85% certain this is a top-5 improvement.

---

### 🏅 #4: Retry Logic with Exponential Backoff and Graceful Degradation

**What it is**: When an API call fails, retry up to 3 times with exponential backoff (1s, 2s, 4s). If all retries fail, gracefully degrade by using mock data and flagging the result.

**Why it's critical for reliability**:
- **APIs are flaky**: Network timeouts, rate limits, temporary outages—these happen. Currently, a single failure during batch processing produces a cryptic error or incomplete results.
- **Graceful degradation**: If Brave Search is down, the tool should still work with OpenCorporates data (and mock search data). The risk score can still be calculated with partial data.
- **Transparency**: Flag results that used fallback data: "⚠️ Online presence data unavailable (API timeout)"

**Implementation approach** (using `tenacity`):

First, add to requirements.txt:
```
tenacity>=8.2.0
```

Then modify the API clients:
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

logger = logging.getLogger(__name__)

class BraveSearchClient:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(requests.RequestException),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _make_request_with_retry(self, query: str, count: int = 20) -> dict:
        """Make API request with automatic retry on failure."""
        return self._make_request(query, count)
    
    def search_company(self, company_name: str) -> OnlinePresence:
        """Search for company with retry and graceful degradation."""
        try:
            return self._search_company_impl(company_name)
        except Exception as e:
            logger.warning(f"All retries failed for {company_name}: {e}")
            # Graceful degradation: return mock with error flag
            presence = self.get_mock_presence(company_name)
            presence.error = f"API unavailable after 3 retries: {e}"
            presence.is_fallback = True
            return presence
```

For the enrichment pipeline, track data quality:
```python
@dataclass
class EnrichedCompany:
    # ... existing fields ...
    
    # Data quality indicators
    brave_fallback: bool = False
    opencorporates_fallback: bool = False
    
    @property
    def data_quality(self) -> str:
        if self.brave_fallback and self.opencorporates_fallback:
            return "low"
        elif self.brave_fallback or self.opencorporates_fallback:
            return "partial"
        return "full"
```

**How users will perceive it**: They won't notice—which is the point. The tool "just works" even under adverse conditions. When degradation occurs, they see a clear indicator.

**Confidence**: 85% certain this is essential for production-readiness.

---

### 🎖️ #5: Configurable Scoring Weights via Settings UI

**What it is**: Add sliders on the Settings page allowing users to adjust the 5 category weights (Online Activity, Corporate Info, Officers, Jurisdiction Risk, External Factors). Persist in session state.

**Why it adds real value**:
- **Different use cases need different weights**: A crypto compliance team might weight jurisdiction risk at 40%. A due diligence firm might prioritize corporate info. The current fixed weights (30/25/20/15/10) are reasonable defaults but shouldn't be immutable.
- **Professional customization**: Investigators feel empowered when they can tune the tool to their mental model.
- **Educational**: Adjusting weights helps users understand what factors drive the score.

**Implementation approach**:

```python
def settings_page():
    st.title("⚙️ Settings")
    
    # ... existing API configuration ...
    
    st.markdown("---")
    st.markdown("### 📊 Scoring Weight Configuration")
    st.markdown("""
    Adjust the importance of each category in the risk score calculation.
    Weights will be normalized to sum to 100%.
    """)
    
    # Load current weights from session state or defaults
    defaults = st.session_state.get("custom_weights", {
        "online_activity": 30,
        "corporate_info": 25,
        "officers_structure": 20,
        "jurisdiction_risk": 15,
        "external_factors": 10,
    })
    
    col1, col2 = st.columns(2)
    
    with col1:
        online = st.slider(
            "🌐 Online Activity",
            min_value=0, max_value=100,
            value=defaults["online_activity"],
            help="Web presence, social media, Wikipedia coverage"
        )
        corporate = st.slider(
            "🏢 Corporate Info",
            min_value=0, max_value=100,
            value=defaults["corporate_info"],
            help="Registration status, company lifespan, address"
        )
        officers = st.slider(
            "👥 Officers & Structure",
            min_value=0, max_value=100,
            value=defaults["officers_structure"],
            help="Number of officers, address matching"
        )
    
    with col2:
        jurisdiction = st.slider(
            "🌍 Jurisdiction Risk",
            min_value=0, max_value=100,
            value=defaults["jurisdiction_risk"],
            help="Offshore vs onshore incorporation"
        )
        external = st.slider(
            "📋 External Factors",
            min_value=0, max_value=100,
            value=defaults["external_factors"],
            help="Regulatory mentions, data confidence"
        )
    
    # Calculate and display normalized weights
    total = online + corporate + officers + jurisdiction + external
    
    if total > 0:
        normalized = {
            "online_activity": online / total,
            "corporate_info": corporate / total,
            "officers_structure": officers / total,
            "jurisdiction_risk": jurisdiction / total,
            "external_factors": external / total,
        }
        
        st.session_state["custom_weights"] = {
            "online_activity": online,
            "corporate_info": corporate,
            "officers_structure": officers,
            "jurisdiction_risk": jurisdiction,
            "external_factors": external,
        }
        st.session_state["normalized_weights"] = normalized
        
        # Visual feedback
        st.markdown("#### Normalized Weights")
        weight_df = pd.DataFrame({
            "Category": ["Online Activity", "Corporate Info", "Officers", "Jurisdiction", "External"],
            "Weight": [f"{v*100:.1f}%" for v in normalized.values()],
        })
        st.dataframe(weight_df, hide_index=True)
        
        if st.button("🔄 Reset to Defaults"):
            st.session_state.pop("custom_weights", None)
            st.session_state.pop("normalized_weights", None)
            st.rerun()
    else:
        st.error("At least one category must have a non-zero weight!")
```

Then use in analysis:
```python
def analyze_companies(df, name_col, jur_col):
    # Get custom weights if configured
    weights = st.session_state.get("normalized_weights", SCORING_WEIGHTS)
    scorer = RiskScorer(weights=weights)
    # ... rest of analysis
```

**How users will perceive it**: "I can configure this for my industry!" Adds a sense of professional-grade flexibility without overwhelming casual users (sliders are optional).

**Confidence**: 75% certain this belongs in top 5. Slightly less critical than the reliability improvements but meaningfully differentiating.

---

## Summary Table

| Rank | Idea | Impact | Effort | Why It's Best |
|------|------|--------|--------|---------------|
| 1 | Single-Company Quick Lookup | 🔥🔥🔥 | Low | Removes biggest UX friction |
| 2 | Smart Caching Layer | 🔥🔥🔥 | Medium | Protects API quota, speeds up UX |
| 3 | Concurrent Enrichment + Progress | 🔥🔥 | Medium | 5-10x batch speed improvement |
| 4 | Retry + Graceful Degradation | 🔥🔥 | Low | Makes tool reliable under real conditions |
| 5 | Configurable Scoring Weights | 🔥 | Low | Professional customization |

---

## Key Insights

All 5 improvements share these qualities:

- **Obviously accretive**: Any user will immediately see the value
- **Pragmatic**: Can be implemented incrementally without architectural rewrites
- **Robustness-focused**: Each makes the tool more reliable or usable
- **Complementary**: They work together—quick lookup benefits from caching, batch mode benefits from concurrency and retries

### Implementation Order Recommendation

1. **Single-Company Quick Lookup** (1-2 hours) - Immediate UX win
2. **Retry Logic** (1 hour) - Add `tenacity`, wrap API calls
3. **Caching Layer** (2-3 hours) - `@st.cache_data` first, SQLite later
4. **Concurrent Enrichment** (3-4 hours) - Refactor pipeline
5. **Configurable Weights** (2 hours) - Settings UI + pass to scorer

Total estimated effort: 9-12 hours for all 5 improvements.

---

## Additional Dependencies Required

```txt
# Add to requirements.txt
tenacity>=8.2.0  # For retry logic
```

---

*Analysis generated: January 9, 2026*
