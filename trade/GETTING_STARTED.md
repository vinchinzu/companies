# Getting Started with Company Verifier Tool

## Quick Start Guide

This guide will help you get up and running with the Company Verification Tool for shell company detection.

## What Was Built

A complete MVP Python tool that:

1. **Verifies company registrations** - UK Companies House & US SEC EDGAR
2. **Screens sanctions lists** - OpenSanctions & ITA Consolidated Screening List
3. **Checks offshore databases** - ICIJ Offshore Leaks (Panama Papers, Pandora Papers, etc.)
4. **Verifies trade activity** - UN Comtrade (country-level) with ImportYeti guidance
5. **Calculates risk scores** - Weighted algorithm with actionable recommendations

## Installation (2 minutes)

### Step 1: Install Dependencies

```bash
cd company-research-tool/trade
pip install requests python-dotenv pandas
```

### Step 2: Configure API Keys (Optional but Recommended)

Edit the `.env` file:

```bash
nano .env
```

Add your API keys (see README.md for registration links):

```env
# For UK company verification (free)
COMPANIES_HOUSE_API_KEY=your_key_here

# For sanctions screening (free tier)
OPENSANCTIONS_API_KEY=your_key_here

# For additional sanctions (free)
ITA_SUBSCRIPTION_KEY=your_key_here

# For trade data (free)
UN_COMTRADE_SUBSCRIPTION_KEY=your_key_here
```

**Note**: The tool works partially without API keys - it will use SEC EDGAR for US companies (no key required) and ICIJ data if downloaded.

### Step 3: (Optional) Download ICIJ Offshore Leaks Data

For offshore entity detection:

```bash
cd data/icij_offshore
wget https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip
unzip full-oldb.LATEST.zip
```

Warning: This is a large download (~1-2 GB).

## Usage Examples

### Test Configuration

```bash
python3 company_verifier.py --check-config
```

### Verify a US Company

```bash
python3 company_verifier.py --name "Apple Inc." --country US
```

**Expected Output**: LOW RISK (Score: 70/100) - Legitimate company

### Verify a UK Company

```bash
python3 company_verifier.py --name "BP PLC" --country GB
```

**Note**: Requires Companies House API key

### With Industry Code (for trade verification)

```bash
python3 company_verifier.py --name "Tesla Inc" --country US --hs-code 87
```

HS Code 87 = Vehicles

### JSON Output (for scripts/automation)

```bash
python3 company_verifier.py --name "Company X" --country US --json > output.json
```

### Save Report to File

```bash
python3 company_verifier.py --name "Company X" --country US --output report.json
```

## Understanding the Output

### Risk Levels

- **🟢 LOW RISK (70-100)**: Company appears legitimate
  - Found in official registry
  - Active status with recent filings
  - No sanctions hits
  - No offshore red flags

- **🟡 MEDIUM RISK (40-69)**: Some concerns, investigate further
  - May have minor issues (dormant, no recent filings, etc.)
  - Requires additional verification

- **🔴 HIGH RISK (0-39)**: Multiple shell company indicators
  - Not found in registry OR
  - Sanctions/PEP hits OR
  - Offshore entity with no activity OR
  - Combination of red flags

### Exit Codes (for automation)

```bash
python3 company_verifier.py --name "Company" --country US
echo $?  # Check exit code
```

- `0` = Low risk
- `1` = Medium risk
- `2` = High risk

Use in scripts:
```bash
if python3 company_verifier.py --name "$COMPANY" --country US --json > /dev/null; then
    echo "Low risk company"
else
    echo "Investigate further"
fi
```

## What Each Module Does

### 1. Registry Checker (`modules/registry_checker.py`)

**UK (Companies House)**:
- Searches by company name
- Retrieves company profile, officers, filings
- Checks status (active, dissolved, etc.)
- Verifies recent filing activity
- Red flags: Dissolved, no filings, no officers

**US (SEC EDGAR)**:
- Searches company tickers database
- Retrieves SEC filings (10-K, 10-Q, etc.)
- Checks entity type
- Red flags: No filings, labeled as "shell company"

### 2. Sanctions Checker (`modules/sanctions_checker.py`)

**OpenSanctions**:
- Screens against global sanctions lists
- Checks for PEPs (Politically Exposed Persons)
- Fuzzy name matching

**ITA Consolidated Screening List**:
- 11 US export control and sanctions lists
- OFAC SDN, BIS Entity List, etc.

### 3. Offshore Checker (`modules/offshore_checker.py`)

**ICIJ Offshore Leaks**:
- Searches Panama Papers, Pandora Papers, Paradise Papers
- 810,000+ offshore entities
- Identifies tax haven jurisdictions
- Red flags: Offshore entity, tax haven, dissolved

### 4. Trade Checker (`modules/trade_checker.py`)

**UN Comtrade**:
- Country-level trade statistics by HS code
- Inference: If country has zero trade in claimed sector → red flag

**ImportYeti Guidance**:
- Generates URL for manual company-level verification
- Free US Bill of Lading search

### 5. Risk Scorer (`modules/risk_scorer.py`)

**Weighted Algorithm**:
- Registry: ±25 points
- Sanctions: ±50 points (most critical)
- Offshore: ±20 points
- Trade: ±15 points

**Scoring Logic**:
- Base score: 50
- Active registry + recent filings: +20
- Sanctions hit: -30 (critical)
- Offshore entity: -15
- Tax haven: -5
- Trade alignment: +10

## Demo Workflow

### Investigating "Suspicious Corp Ltd"

```bash
# Step 1: Initial screening
python3 company_verifier.py --name "Suspicious Corp Ltd" --country GB --output case_001.json

# Step 2: Review the output
#   - Risk score: 25 (HIGH RISK)
#   - Red flags:
#     • Company dissolved 2 years ago
#     • Found in Panama Papers
#     • Tax haven jurisdiction (BVI)
#     • No recent filings

# Step 3: Manual verification
# Visit the ImportYeti URL in the output
# Check company's claimed website
# Verify beneficial owners

# Step 4: Document findings
# JSON report saved to case_001.json for audit trail
```

## API Key Priority

**Start with these (highest value)**:

1. **SEC EDGAR** - Already works (no key needed!)
2. **ICIJ Data** - Free download, no API needed
3. **Companies House** - Free UK registry (required for UK companies)
4. **OpenSanctions** - Free tier for non-commercial use (best sanctions coverage)

**Optional additions**:

5. **ITA Trade.gov** - Additional US sanctions lists
6. **UN Comtrade** - Trade statistics (limited value without company-level data)

## Limitations to Understand

### 1. Company-Level Trade Data Not Automated

- UN Comtrade = country/product level only
- ImportYeti = requires manual web search
- **Workaround**: Tool generates ImportYeti URL for you

### 2. Registry Coverage

- Currently: UK + US only
- Other countries: Manual check via national registries
- **Future**: Can add more registries as modules

### 3. False Positives

**Legitimate companies that may score poorly**:
- Brand new startups (< 1 year old)
- Dormant holding companies
- Recently acquired companies

**Always verify manually before conclusions**

### 4. False Negatives

**Sophisticated shells may evade**:
- Using legitimate-looking structures
- Filed proper paperwork
- No sanctions (yet)
- Not in leaked databases

**Use as one tool among many**

## Tips for Investigations

### Best Practices

1. **Multiple searches**: Try name variations
   ```bash
   python3 company_verifier.py --name "Apple Inc" --country US
   python3 company_verifier.py --name "Apple Incorporated" --country US
   ```

2. **Cross-reference**: Use with other sources
   - Company website
   - LinkedIn employee counts
   - News articles
   - Domain registration age

3. **Document everything**: Save JSON reports
   ```bash
   python3 company_verifier.py --name "$COMPANY" --country US --output "reports/$(date +%Y%m%d)_$COMPANY.json"
   ```

4. **Check officers/owners**: In full investigation, screen all related persons

5. **Manual trade verification**: Always check ImportYeti URL for US companies

### Red Flag Combinations

**🚨 Immediate Alert** (investigate urgently):
- Sanctions hit + Offshore entity
- Not found in registry + Claims to be established business
- Dissolved + Recently used in transaction

**⚠️ Investigate Further**:
- Offshore + Tax haven + No trade
- Dormant + No filings for years
- Recently incorporated + Large transactions

**ℹ️ Context Needed**:
- No filings alone (may be startup)
- Offshore alone (many legitimate reasons)
- No trade data (may be services company)

## Next Steps

### Enhance Your Setup

1. **Get API keys** (5 minutes each)
   - See README.md for registration links
   - All have free tiers

2. **Download ICIJ data** (one-time, 30 minutes)
   - Adds 810K offshore entities
   - Significantly improves detection

3. **Test with known cases**
   - Try legitimate companies (Apple, Microsoft, etc.)
   - Try known shell companies from news articles
   - Calibrate your interpretation

### Automation Ideas

**Batch processing**:
```bash
#!/bin/bash
while IFS= read -r company; do
    python3 company_verifier.py --name "$company" --country US --json >> batch_results.jsonl
done < companies.txt
```

**Integration with case management**:
```python
import subprocess
import json

result = subprocess.run(
    ['python3', 'company_verifier.py', '--name', company_name, '--country', 'US', '--json'],
    capture_output=True,
    text=True
)
data = json.loads(result.stdout)
risk_score = data['risk_assessment']['risk_score']
```

**Alerting**:
```bash
SCORE=$(python3 company_verifier.py --name "$COMPANY" --country US --json | jq '.risk_assessment.risk_score')
if [ $SCORE -lt 40 ]; then
    echo "HIGH RISK ALERT: $COMPANY (Score: $SCORE)" | mail -s "Shell Company Alert" investigator@example.com
fi
```

## Troubleshooting

### "Company not found"

- Try name variations (Inc., Ltd., etc.)
- Check spelling
- Verify correct country
- May be registered in different jurisdiction

### "API not configured"

- Edit `.env` file
- Add the relevant API key
- Some features work without keys (SEC EDGAR)

### "ICIJ data not loaded"

- Download CSV files to `data/icij_offshore/`
- See installation section above

### ImportErrors

```bash
pip install requests python-dotenv pandas
```

## File Reference

```
trade/
├── company_verifier.py          # Main script - RUN THIS
├── config.py                    # API key configuration
├── .env                         # YOUR API KEYS (edit this)
├── requirements.txt             # Dependencies
├── README.md                    # Full documentation
├── GETTING_STARTED.md           # This file
├── API_DOCUMENTATION.md         # API reference
├── ARCHITECTURE.md              # System design
├── modules/                     # Verification modules
├── utils/                       # Helper functions
└── data/icij_offshore/          # ICIJ CSV files (download)
```

## Support & Resources

### Documentation

- **README.md** - Complete user guide
- **API_DOCUMENTATION.md** - Detailed API specs
- **ARCHITECTURE.md** - Technical architecture

### External Resources

- [OpenSanctions](https://www.opensanctions.org/)
- [Companies House](https://developer.company-information.service.gov.uk/)
- [SEC EDGAR](https://www.sec.gov/edgar/searchedgar/companysearch.html)
- [ICIJ Offshore Leaks](https://offshoreleaks.icij.org/)
- [UN Comtrade](https://comtradeplus.un.org/)
- [ImportYeti](https://www.importyeti.com/)

## Quick Reference Card

```bash
# Check configuration
python3 company_verifier.py --check-config

# Basic verification (US)
python3 company_verifier.py --name "Company Name" --country US

# Basic verification (UK)
python3 company_verifier.py --name "Company Name" --country GB

# With trade code
python3 company_verifier.py --name "Company" --country US --hs-code 85

# JSON output
python3 company_verifier.py --name "Company" --country US --json

# Save to file
python3 company_verifier.py --name "Company" --country US --output report.json

# Get help
python3 company_verifier.py --help
```

---

**You're ready to start investigating! 🕵️**

Begin with:
```bash
python3 company_verifier.py --name "Apple Inc." --country US
```

This should return LOW RISK (Score: 70/100) as a test.
