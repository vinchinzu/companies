# Company Verification Tool - Shell Company Detection MVP

A Python-based open-source intelligence (OSINT) tool for investigating companies and detecting potential shell company indicators. Built for financial crime investigators, compliance professionals, and researchers working on anti-money laundering (AML) investigations.

## Overview

This tool correlates data from multiple free/open-source APIs and datasets to assess whether a company shows signs of being a legitimate business or a potential shell company used for illicit purposes.

### What It Checks

1. **Registry Verification** - Official company registrations (UK Companies House, US SEC EDGAR)
2. **Sanctions Screening** - Global sanctions lists and politically exposed persons (OpenSanctions, ITA CSL)
3. **Offshore Entities** - Presence in leaked offshore databases (ICIJ Offshore Leaks)
4. **Trade Activity** - Business operations verification (UN Comtrade country-level, ImportYeti guidance)

### Risk Indicators Detected

- Company not found in official registries
- Dissolved or inactive status
- No recent filings or dormant
- Sanctions or PEP involvement
- Offshore entity connections
- Tax haven jurisdictions
- Zero trade activity in claimed sector
- Recently incorporated with no history

## Features

- ✅ Free and open-source data sources
- ✅ No expensive API subscriptions required (free tier access)
- ✅ Parallel API queries for speed
- ✅ Risk scoring algorithm with weighted factors
- ✅ JSON output for automation
- ✅ CLI interface for easy use
- ✅ Detailed red flag reporting
- ✅ Actionable recommendations

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Internet connection

### Setup

1. **Clone or download this repository**:
```bash
cd company-research-tool/trade
```

2. **Create virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure API keys**:
```bash
cp .env.example .env
nano .env  # Edit with your API keys
```

### API Key Registration

#### Required for Full Functionality

1. **UK Companies House** (Free, required for UK companies)
   - Register: https://developer.company-information.service.gov.uk/
   - Create account → Get API key
   - Add to `.env`: `COMPANIES_HOUSE_API_KEY=your_key`

2. **OpenSanctions** (Free tier for non-commercial)
   - Sign up: https://www.opensanctions.org/api/
   - Free for media, NGOs, researchers
   - Add to `.env`: `OPENSANCTIONS_API_KEY=your_key`

#### Optional (Enhances Coverage)

3. **ITA Trade.gov** (Free)
   - Register: https://developer.trade.gov/
   - Subscribe to "Data Services Platform APIs"
   - Add to `.env`: `ITA_SUBSCRIPTION_KEY=your_key`

4. **UN Comtrade** (Free)
   - Register: https://comtradedeveloper.un.org/
   - Subscribe to free tier
   - Add to `.env`: `UN_COMTRADE_SUBSCRIPTION_KEY=your_key`

#### ICIJ Offshore Leaks Database

Download the CSV files (free, no API key needed):

```bash
# Download (warning: ~1-2 GB compressed)
cd data/icij_offshore
wget https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip

# Extract
unzip full-oldb.LATEST.zip
```

Files needed:
- `nodes-entities.csv`
- `nodes-officers.csv`
- `relationships.csv`

### Verify Configuration

```bash
python company_verifier.py --check-config
```

This will show which APIs are configured and whether ICIJ data is loaded.

## Usage

### Basic Usage

**Check a US company:**
```bash
python company_verifier.py --name "Apple Inc." --country US
```

**Check a UK company:**
```bash
python company_verifier.py --name "BP PLC" --country GB
```

**With trade verification (HS code for electronics):**
```bash
python company_verifier.py --name "Tech Corp" --country US --hs-code 85
```

### Advanced Usage

**JSON output for automation:**
```bash
python company_verifier.py --name "Company X" --country US --json > results.json
```

**Save to file:**
```bash
python company_verifier.py --name "Company X" --country GB --output report.json
```

**Exit codes:**
- `0` - Low risk (legitimate)
- `1` - Medium risk (investigate)
- `2` - High risk (shell company indicators)

### Command-Line Options

```
--name NAME          Company name to verify (required)
--country CODE       Country code: US, GB (default: US)
--hs-code CODE       HS product code for trade verification (optional)
--json               Output as JSON
--output FILE        Save results to file
--check-config       Check API configuration
```

## Example Output

```
╔══════════════════════════════════════════════════════════════╗
║          Company Verification Tool - Shell Detection         ║
║                           MVP v1.0                           ║
╚══════════════════════════════════════════════════════════════╝

Investigating: Apple Inc.
Jurisdiction: US

======================================================================
  1. REGISTRY VERIFICATION
======================================================================
Checking official company registries...
✓ Company found: APPLE INC
  Status: active
  CIK: 0000320193
  SIC: 3571 - Electronic Computers
  Recent 10-K: 2024-10-31

======================================================================
  2. SANCTIONS SCREENING
======================================================================
Screening against sanctions lists and PEPs...
✓ No sanctions or PEP matches found
  Sources checked: OpenSanctions, ITA CSL

======================================================================
  3. OFFSHORE ENTITIES CHECK
======================================================================
Searching ICIJ Offshore Leaks database...
✓ No offshore entity matches found

======================================================================
  4. TRADE ACTIVITY VERIFICATION
======================================================================
Checking trade records...
  Manual verification: https://www.importyeti.com/search?q=Apple+Inc.
  UN Comtrade provides country-level data only.

======================================================================
  5. RISK ASSESSMENT
======================================================================

🟢 LOW RISK (Score: 85/100)
Confidence: 90%

RECOMMENDATIONS:
  LOW RISK: Company appears legitimate
  Standard due diligence recommended
```

## Project Structure

```
trade/
├── company_verifier.py          # Main CLI script
├── config.py                    # Configuration management
├── modules/                     # Verification modules
│   ├── registry_checker.py      # UK Companies House + SEC EDGAR
│   ├── sanctions_checker.py     # OpenSanctions + ITA CSL
│   ├── offshore_checker.py      # ICIJ Offshore Leaks
│   ├── trade_checker.py         # UN Comtrade
│   └── risk_scorer.py           # Risk scoring engine
├── utils/                       # Utilities
│   ├── api_client.py            # HTTP client with retry logic
│   └── helpers.py               # Helper functions
├── data/
│   └── icij_offshore/           # ICIJ CSV files
├── requirements.txt
├── .env.example
├── API_DOCUMENTATION.md         # Detailed API docs
├── ARCHITECTURE.md              # System architecture
└── README.md                    # This file
```

## Data Sources

| Source | Type | Coverage | Free? |
|--------|------|----------|-------|
| UK Companies House | Registry | UK companies | ✓ Yes |
| SEC EDGAR | Registry | US public companies | ✓ Yes |
| OpenSanctions | Sanctions/PEP | Global | ✓ Free tier |
| ITA CSL | Sanctions | 11 US lists | ✓ Yes |
| ICIJ Offshore Leaks | Offshore entities | 810K+ entities | ✓ Yes |
| UN Comtrade | Trade (country-level) | Global | ✓ Yes |
| ImportYeti | Trade (company-level) | US imports | Manual |

## Limitations

1. **Company-Level Trade Data**: UN Comtrade only provides country/product aggregates. Company-specific shipments require manual ImportYeti lookups or paid APIs.

2. **Registry Coverage**: Currently supports UK and US only. Other jurisdictions require manual checking via national registries.

3. **Data Lag**: APIs may have delayed updates (days to weeks depending on source).

4. **False Positives**: Legitimate startups or dormant holding companies may score poorly.

5. **False Negatives**: Sophisticated shell companies may evade detection.

6. **API Rate Limits**: Free tiers have request limits (see API_DOCUMENTATION.md).

## Best Practices

### Investigation Workflow

1. **Initial Screening**:
   ```bash
   python company_verifier.py --name "Target Company" --country US
   ```

2. **Review Red Flags**: Check all flagged issues in the output

3. **Manual Verification**:
   - Visit ImportYeti URL for trade records
   - Check company website and public presence
   - Verify beneficial ownership
   - Review financial statements

4. **Document Findings**: Save JSON output for audit trail
   ```bash
   python company_verifier.py --name "Company" --country GB --output case_123.json
   ```

### Interpreting Risk Scores

- **70-100 (Low)**: Likely legitimate, standard due diligence
- **40-69 (Medium)**: Some red flags, investigate further
- **0-39 (High)**: Multiple shell indicators, high risk

### Red Flags Priority

🔴 **Critical** (Investigate immediately):
- Sanctions hits
- PEP involvement
- Company not found in registry

🟡 **Warning** (Review carefully):
- Offshore leaks presence
- No recent filings
- Dissolved status
- Tax haven jurisdiction

🟢 **Info** (Context-dependent):
- Recently incorporated
- No trade data (may not export)

## Contributing

This is an MVP. Potential enhancements:

- [ ] Add more country registries (EU BRIS, etc.)
- [ ] Integrate paid ImportYeti API
- [ ] Machine learning risk scoring
- [ ] Web UI with Streamlit
- [ ] Batch processing mode
- [ ] PDF report generation
- [ ] Officer screening against sanctions
- [ ] Relationship graph visualization
- [ ] Historical monitoring/alerts

## Security and Compliance

### Data Handling

- API keys stored in `.env` (not committed to git)
- No persistent storage of PII
- Results contain only verification outcomes
- Comply with all API Terms of Service

### Ethical Use

This tool is intended for:
- ✓ Anti-money laundering investigations
- ✓ Due diligence and compliance
- ✓ Journalism and research
- ✓ Academic studies

**Not for**:
- ✗ Harassment or stalking
- ✗ Illegal surveillance
- ✗ Commercial data resale
- ✗ Violating privacy laws

### Legal Disclaimer

This tool provides risk indicators based on open-source data. It does not constitute:
- Legal advice
- Financial advice
- Definitive proof of wrongdoing
- Replacement for professional due diligence

Always consult legal and compliance professionals for official determinations.

## Troubleshooting

### "API key not configured"

Edit `.env` and add the required API key. See "API Key Registration" section above.

### "ICIJ data not loaded"

Download and extract ICIJ Offshore Leaks CSV files to `data/icij_offshore/`. See Installation section.

### "Rate limit exceeded (429)"

Wait for the rate limit window to reset (typically 5 minutes). Consider:
- Spacing out requests
- Caching results
- Upgrading to paid tiers (if available)

### "Company not found"

Try:
- Different name variations (with/without Ltd, Inc, etc.)
- Check spelling
- Verify correct country code
- Company may not be registered in that jurisdiction

### Import errors

Ensure virtual environment is activated and dependencies installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Resources

### Documentation

- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Detailed API reference
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and architecture

### External Links

- [OpenSanctions](https://www.opensanctions.org/)
- [Companies House API](https://developer.company-information.service.gov.uk/)
- [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [ICIJ Offshore Leaks](https://offshoreleaks.icij.org/)
- [ITA Data Services](https://developer.trade.gov/)
- [UN Comtrade](https://comtradedeveloper.un.org/)
- [ImportYeti](https://www.importyeti.com/)

## License

This tool is provided for research and educational purposes. Respect all applicable laws and API terms of service.

ICIJ data is licensed under:
- Database: Open Database License (ODbL)
- Content: Creative Commons Attribution-ShareAlike

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API_DOCUMENTATION.md
3. Verify configuration with `--check-config`

---

**Version**: 1.0 MVP
**Last Updated**: 2026-01-21
**Built with**: Python 3.8+, OpenSanctions, Companies House, SEC EDGAR, ICIJ Offshore Leaks
