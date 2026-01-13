# Company Research Tool

A comprehensive web application for investigating companies, detecting shell company indicators, screening against sanctions lists, and assessing fraud risk. Built for investigators, compliance teams, and due diligence professionals.

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.30+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🎯 Try the Demo First!

**NEW: Interactive Network Visualization** - Works immediately with zero setup!

```bash
# Quick start - just 2 commands!
pip install -r requirements.txt
streamlit run app.py
```

Navigate to **"Network Investigation"** to explore a $6.9B+ fraud network with interactive graphs. No configuration needed!

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/company-research-tool.git
cd company-research-tool

# Run the setup wizard (recommended for first time)
python setup_wizard.py

# Or manual setup:
pip install -r requirements.txt
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

---

## What This Tool Does

### 1. Company Risk Assessment
Upload a list of companies and get automated risk scores based on:
- Online presence (websites, social media, news coverage)
- Corporate registry data (status, age, officers)
- Jurisdiction risk (offshore vs onshore)
- Historical fraud patterns

### 2. Sanctions Screening
Screen companies against multiple sanctions databases:
- **OFAC** - US Treasury sanctions (10,000+ entities)
- **OpenSanctions Consolidated** - Global sanctions (100,000+ entities)
- **PEPs** - Politically Exposed Persons (1,000,000+ entities)

### 3. Offshore Leaks Search
Check companies against the **ICIJ Offshore Leaks** database:
- Panama Papers
- Paradise Papers
- Pandora Papers
- 810,000+ offshore entities

### 4. Fraud Database
Browse 7,000+ known fraud cases including:
- SEC enforcement actions
- Ponzi schemes (BitConnect, HyperFund)
- Crypto fraud (FTX, Terraform Labs)
- Accounting fraud (Enron, Wirecard)

### 5. Network Investigation 🌟 **DEMO READY**
Interactive fraud network visualization with:
- **Pre-loaded $6.9B crypto fraud network** (works immediately!)
- 27 interconnected entities (companies, executives, addresses, cases)
- Drag-and-drop network graph with filtering
- Network analysis (centrality, bridges, clusters)
- **Zero setup required** - just load the page!

---

## Features at a Glance

| Feature | Description | Setup Required |
|---------|-------------|----------------|
| **🕸️ Network Investigation** | **Interactive fraud network demo** | ✅ **None - works immediately!** |
| **Upload & Analyze** | Batch process Excel/CSV files | Optional APIs |
| **Sanctions Screening** | Check against OFAC and global sanctions | Download required |
| **Fraud Database** | Browse 7,000+ fraud cases | Build required |
| **Risk Scoring** | 0-4 scale with detailed breakdowns | Optional APIs |
| **Data Management** | Download and update databases | Internet connection |
| **Export Results** | CSV and Excel export | None |

---

## Installation

### Requirements
- Python 3.9 or higher
- 2 GB disk space (for full database downloads)
- Internet connection (for API access and downloads)

### Option 1: Setup Wizard (Recommended)

The setup wizard guides you through installation:

```bash
python setup_wizard.py
```

This will:
1. Check dependencies and install if needed
2. Create required directories
3. Configure API keys (optional)
4. Download sanctions databases
5. Build the fraud database

### Option 2: Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys (optional)
nano .env

# Download databases
python -c "from scrapers.opensanctions import OpenSanctionsClient; c = OpenSanctionsClient(); c.download_dataset('ofac_press_releases'); c.download_names_list()"

# Build fraud database
python combine_all_sources.py

# Start the application
streamlit run app.py
```

---

## Usage Guide

### Analyzing Companies

1. **Prepare your data**: Create an Excel or CSV file with company names
   ```
   Company Name,Jurisdiction
   Acme Corp,US-DE
   Global Trading Ltd,KY
   ```

2. **Upload**: Go to "Upload & Analyze" and upload your file

3. **Map columns**: Select which column contains company names

4. **Analyze**: Click "Analyze Companies" to run the assessment

5. **Review results**:
   - Red = High Risk (score < 2.0)
   - Yellow = Medium Risk (score 2.0-3.0)
   - Green = Low Risk (score > 3.0)

6. **Export**: Download results as CSV or Excel

### Sanctions Screening

1. Go to "Sanctions Screening"
2. **Quick check**: Enter a single company name
3. **Batch check**: Upload a file with multiple companies
4. Results show:
   - EXACT MATCH - Company is on sanctions list
   - PARTIAL MATCH - Similar name found, investigate
   - CLEAR - No matches found

### Browsing Fraud Database

1. Go to "Fraud Database"
2. Use filters to narrow by:
   - Fraud type (Ponzi, Securities, Accounting)
   - Source (SEC, DOJ, OFAC)
   - Jurisdiction
3. Click any case to see full details

---

## Data Sources

### Included Databases

| Database | Entities | Update | Size |
|----------|----------|--------|------|
| SEC Enforcement | 1,500+ | Manual | 500 KB |
| OpenSanctions OFAC | 10,000+ | Daily | 10 MB |
| OpenSanctions Consolidated | 100,000+ | Daily | 50 MB |
| ICIJ Offshore Leaks | 810,000+ | Periodic | 500 MB |

### External APIs (Optional)

| API | Purpose | Free Tier |
|-----|---------|-----------|
| [Brave Search](https://api-dashboard.search.brave.com) | Web presence scoring | 2,000/month |
| [OpenCorporates](https://opencorporates.com) | Corporate registry data | 200/month |

**Note**: The tool works without API keys using mock data for demonstration.

---

## Risk Scoring Framework

Companies are scored on a 0-4 scale across five categories:

| Category | Weight | What It Measures |
|----------|--------|------------------|
| **Online Activity** | 30% | Website, social media, Wikipedia, news |
| **Corporate Info** | 25% | Status, age, registered address |
| **Officers & Structure** | 20% | Number of officers, address matching |
| **Jurisdiction Risk** | 15% | Offshore vs onshore incorporation |
| **External Factors** | 10% | Regulatory mentions, data quality |

### Risk Levels

| Score | Level | Meaning |
|-------|-------|---------|
| > 3.0 | Low Risk | Legitimate indicators |
| 2.0 - 3.0 | Medium Risk | Some concerns, review needed |
| < 2.0 | High Risk | Shell company indicators |

### High-Risk Jurisdictions

These jurisdictions receive automatic risk flags:
- Cayman Islands (KY)
- British Virgin Islands (VG)
- Panama (PA)
- Belize (BZ)
- Seychelles (SC)

---

## Project Structure

```
company-research-tool/
├── app.py                    # Main Streamlit application
├── setup_wizard.py           # First-time setup script
├── combine_all_sources.py    # Database builder
├── requirements.txt          # Python dependencies
│
├── scrapers/
│   ├── opensanctions.py      # OpenSanctions client
│   ├── icij_offshore.py      # ICIJ Offshore Leaks client
│   ├── sec_scraper.py        # SEC enforcement scraper
│   └── pdf_extractor.py      # SEC PDF extraction
│
├── enrichment/
│   ├── brave_search.py       # Brave Search API client
│   ├── opencorporates.py     # OpenCorporates API client
│   ├── web_presence_scorer.py # Web presence scoring
│   └── enrichment_pipeline.py # Data orchestration
│
├── scoring/
│   └── risk_scorer.py        # Risk scoring engine
│
├── data/
│   ├── examples/             # Sample data files
│   ├── opensanctions/        # Downloaded sanctions data
│   └── icij/                 # Downloaded ICIJ data
│
└── docs/
    └── BRAVE_API_RESPONSE.md # API documentation
```

---

## Configuration

### Environment Variables

Create a `.env` file:

```env
# API Keys (optional - enables real-time data)
BRAVE_API_KEY=your_key_here
OPENCORPORATES_API_TOKEN=your_token_here

# Rate limiting (seconds between API requests)
RATE_LIMIT_DELAY=2
```

### Getting API Keys

**Brave Search API:**
1. Visit https://api-dashboard.search.brave.com
2. Create a free account
3. Generate an API key
4. Free tier: 2,000 queries/month

**OpenCorporates API:**
1. Visit https://opencorporates.com
2. Sign up for an account
3. Request API access
4. Free tier: 200 requests/month

---

## Command Reference

| Command | Description |
|---------|-------------|
| `streamlit run app.py` | Start the web application |
| `python setup_wizard.py` | Run the setup wizard |
| `python combine_all_sources.py` | Rebuild fraud database |
| `python extract_all_pdfs.py` | Extract data from SEC PDFs |

### Downloading Data

```python
# Download OFAC sanctions
from scrapers.opensanctions import OpenSanctionsClient
client = OpenSanctionsClient()
client.download_dataset('ofac_press_releases')

# Download ICIJ Offshore Leaks
from scrapers.icij_offshore import ICIJOffshoreClient
client = ICIJOffshoreClient()
client.download_database()
```

---

## Troubleshooting

### "No sanctions data found"
Run the setup wizard or manually download:
```bash
python -c "from scrapers.opensanctions import OpenSanctionsClient; OpenSanctionsClient().download_names_list()"
```

### "API key not configured"
The tool works without API keys using mock data. For real data:
1. Get free API keys (see Configuration section)
2. Add to `.env` file
3. Restart the application

### "PDF extraction failed"
Install PyMuPDF:
```bash
pip install pymupdf
```

### "Import error"
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

---

## Use Cases

### Due Diligence
Screen potential business partners, vendors, or acquisition targets before engagement.

### Compliance
Document sanctions screening for regulatory requirements. Export results for audit trails.

### Investigation
Research fraud patterns, extract entities from legal documents, build case timelines.

### Training
Demonstrate shell company red flags using mock data mode.

---

## Limitations

- **Data Currency**: Sanctions lists update daily; local copies may lag
- **False Positives**: New/private companies may appear high-risk due to limited data
- **Jurisdiction Generalization**: Legitimate businesses use "high-risk" jurisdictions for valid reasons
- **API Limits**: Free tiers restrict batch processing volume

---

## Contributing

Contributions welcome! Areas for improvement:
- Additional data sources (beneficial ownership, adverse media)
- Machine learning for risk scoring
- Enhanced PDF extraction with NLP
- Multi-language support

---

## License

MIT License - Free for commercial and non-commercial use.

---

## Acknowledgments

Data sources:
- [OpenSanctions](https://www.opensanctions.org/) - Open-source sanctions data
- [ICIJ Offshore Leaks](https://offshoreleaks.icij.org/) - Offshore entity database
- [SEC EDGAR](https://www.sec.gov/edgar) - SEC filings and enforcement actions
- [Brave Search](https://brave.com/search/api/) - Web search API
- [OpenCorporates](https://opencorporates.com/) - Corporate registry data
