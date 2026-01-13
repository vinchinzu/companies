# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Company Research Tool is a Streamlit web application for investigating companies for potential shell company indicators, sanctions exposure, and fraud risk. It combines data from multiple sources:

- **Brave Search API** - Web presence and online activity scoring
- **OpenCorporates API** - Corporate registry data
- **OpenSanctions** - OFAC and global sanctions data
- **ICIJ Offshore Leaks** - Panama Papers, Paradise Papers, etc.
- **SEC Enforcement** - Fraud cases and litigation

## Commands

### Run the application
```bash
streamlit run app.py
```

### First-time setup (interactive)
```bash
python setup_wizard.py
```

### Build/update the fraud database
```bash
python combine_all_sources.py
```

### Extract data from SEC PDFs
```bash
python extract_all_pdfs.py
```

### Download databases manually
```python
# OFAC sanctions
from scrapers.opensanctions import OpenSanctionsClient
client = OpenSanctionsClient()
client.download_dataset('ofac_press_releases')
client.download_names_list()

# ICIJ Offshore Leaks
from scrapers.icij_offshore import ICIJOffshoreClient
client = ICIJOffshoreClient()
client.download_database()
```

### Install dependencies
```bash
pip install -r requirements.txt
```

## Architecture

```
company-research-tool/
├── app.py                    # Main Streamlit application (7 pages)
├── setup_wizard.py           # First-time setup script
├── combine_all_sources.py    # Database builder
├── extract_all_pdfs.py       # PDF extraction script
├── config.py                 # Configuration and environment variables
│
├── scrapers/
│   ├── opensanctions.py      # OpenSanctions OFAC client
│   ├── icij_offshore.py      # ICIJ Offshore Leaks client
│   ├── sec_scraper.py        # SEC enforcement case scraper
│   ├── data_compiler.py      # Dataset compilation (real + synthetic)
│   └── pdf_extractor.py      # PDF extraction for SEC complaints
│
├── enrichment/
│   ├── brave_search.py       # Brave Search API client
│   ├── opencorporates.py     # OpenCorporates API client
│   ├── web_presence_scorer.py # Web presence scoring from Brave API
│   └── enrichment_pipeline.py # Combined enrichment orchestration
│
├── scoring/
│   └── risk_scorer.py        # Weighted risk scoring engine (0-4 scale)
│
├── scripts/                  # Utility scripts
│   ├── download_*.py         # Various PDF downloaders
│   ├── scrape_*.py           # SEC scrapers
│   └── import_*.py           # Data importers
│
├── ui/
│   ├── charts.py             # Plotly chart components
│   └── network_viz.py        # PyVis network visualization
│
├── data/
│   ├── examples/             # Sample data files (included in repo)
│   ├── opensanctions/        # Downloaded sanctions data (.gitignored)
│   ├── icij/                 # Downloaded ICIJ data (.gitignored)
│   └── pdfs/                 # Downloaded SEC PDFs (.gitignored)
│
└── docs/
    └── BRAVE_API_RESPONSE.md # Brave API response documentation
```

## Key Components

### Risk Scoring Framework
Uses a weighted 0-4 scale (GPA-like):
- **Online Activity (30%)**: Hit count, social media, Wikipedia
- **Corporate Info (25%)**: Status, lifespan, registered address
- **Officers & Structure (20%)**: Officer count, address matching
- **Jurisdiction Risk (15%)**: High-risk offshore locations
- **External Factors (10%)**: Regulatory mentions, data confidence

Risk levels: >3.0 = Low Risk, 2.0-3.0 = Medium Risk, <2.0 = High Risk

### Web Presence Scoring
The `WebPresenceScorer` in `enrichment/web_presence_scorer.py` analyzes Brave API responses to detect:
- Legitimate company indicators (LinkedIn, Wikipedia, news coverage)
- Shell company red flags (no online presence, fraud keywords)
- Relevance filtering (ignores unrelated search results)

### Sanctions Screening
Screen companies against:
- OFAC press releases (10,000+ entities)
- Consolidated sanctions (100,000+ entities)
- PEPs - Politically Exposed Persons (1,000,000+ entities)
- ICIJ Offshore Leaks (810,000+ entities)

### High-Risk Jurisdictions
Defined in `config.py`:
- **High**: ky (Cayman), vg (BVI), pa (Panama), bz (Belize), sc (Seychelles), ae (UAE), hk (Hong Kong)
- **Medium**: us_de (Delaware), gb (UK), sg (Singapore)

## Configuration

Set API keys in `.env` file (copy from `.env.example`):
```
BRAVE_API_KEY=your_key
OPENCORPORATES_API_TOKEN=your_token
RATE_LIMIT_DELAY=2
```

Both APIs have mock fallbacks for demo use without keys.

## Data Flow

1. User uploads Excel/CSV with company names
2. `EnrichmentPipeline` fetches data from Brave Search + OpenCorporates
3. `WebPresenceScorer` analyzes search results
4. `RiskScorer` calculates weighted risk scores
5. Sanctions screening checks against OFAC/ICIJ databases
6. Results displayed with visualizations and export options

## App Pages

1. **Home** - Dashboard with database statistics
2. **Upload & Analyze** - Batch company risk assessment
3. **Sanctions Screening** - OFAC/sanctions lookup
4. **Fraud Database** - Browse 7,000+ fraud cases
5. **Network Investigation** - Interactive fraud network visualization
6. **Data Management** - Download and update databases
7. **Settings** - API configuration

## Network Visualization

The Network Investigation page (`ui/network_viz.py`) provides interactive fraud network analysis:

**Demo Dataset:** `data/examples/fraud_network_demo.json` contains a curated crypto fraud network with:
- 11 companies (FTX, Alameda, Terraform Labs, BitConnect, etc.)
- 8 persons (executives, founders)
- 4 addresses (registered offices)
- 4 legal cases (SEC enforcement actions)
- 38 relationship edges

**Features:**
- Interactive node-link diagram (drag, zoom, click)
- Filter by cluster (FTX Network, Terra/Luna, Crypto Contagion, BitConnect)
- Filter by entity type (company, person, address, case)
- Focus on specific entity and its connections
- Network metrics (centrality, bridges, density)
- Entity details table with risk scores

## Database Statistics

- **Fraud Database**: 7,000+ cases from SEC, OFAC, synthetic
- **OFAC Names**: 10,000+ sanctioned entities
- **ICIJ Offshore**: 810,000+ offshore entities (optional download)
