# Company Verification Tool - MVP Architecture

## Overview

This tool helps investigators identify potential shell companies by correlating data from multiple open-source intelligence (OSINT) sources. It takes a company name and optional country, then queries various APIs and datasets to build a risk profile.

## Architecture Design

### High-Level Flow

```
┌─────────────────┐
│   User Input    │
│ (Company Name)  │
└────────┬────────┘
         │
         v
┌─────────────────────────────────────────┐
│         Orchestrator Module             │
│  - Validates input                      │
│  - Dispatches to verification modules   │
│  - Aggregates results                   │
│  - Calculates risk score                │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────────────────┐
│              Parallel Verification Modules           │
├──────────────┬──────────────┬──────────────────────┤
│   Registry   │  Sanctions   │  Offshore/Trade      │
│   Checker    │  Checker     │  Checker             │
└──────────────┴──────────────┴──────────────────────┘
         │
         v
┌─────────────────────────────────────────┐
│         Risk Scoring Engine             │
│  - Weighted scoring algorithm           │
│  - Red flag detection                   │
│  - Confidence scoring                   │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────┐
│         Report Generator                │
│  - JSON output                          │
│  - Human-readable summary               │
│  - Risk flag details                    │
└─────────────────────────────────────────┘
```

## Core Components

### 1. Registry Verification Module (`registry_checker.py`)

**Purpose**: Verify company registration and check activity status

**Data Sources**:
- UK Companies House API (for UK companies)
- SEC EDGAR API (for US companies)
- Extensible for other jurisdictions

**Checks Performed**:
- Company existence
- Registration status (active/dissolved/struck off)
- Recent filing activity (accounts, confirmations)
- Officers and beneficial owners
- Company age

**Red Flags**:
- No registration found
- Dissolved or struck-off status
- No recent filings (dormant)
- Recently incorporated (< 1 year)
- Missing officer information
- Frequent address changes

**Output**:
```python
{
    'found': bool,
    'status': str,  # 'active', 'dissolved', 'not_found'
    'jurisdiction': str,
    'incorporation_date': str,
    'last_filing_date': str,
    'officers_count': int,
    'has_psc': bool,  # Persons with Significant Control
    'address': str,
    'red_flags': [str],
    'confidence': float  # 0.0-1.0
}
```

### 2. Sanctions Screening Module (`sanctions_checker.py`)

**Purpose**: Screen against global sanctions lists and PEP databases

**Data Sources**:
- OpenSanctions API (primary)
- ITA Consolidated Screening List API (secondary)

**Checks Performed**:
- Direct name matching
- Fuzzy matching for variations
- Officer/beneficial owner screening
- Related entity screening

**Red Flags**:
- Direct sanctions hit
- PEP involvement
- Related entity sanctioned
- High-risk jurisdiction

**Output**:
```python
{
    'sanctions_hits': int,
    'pep_hits': int,
    'matches': [{
        'name': str,
        'type': str,  # 'sanctions', 'pep'
        'source': str,
        'program': str,
        'confidence': float
    }],
    'red_flags': [str],
    'confidence': float
}
```

### 3. Offshore Entities Module (`offshore_checker.py`)

**Purpose**: Detect presence in offshore leaks databases

**Data Sources**:
- ICIJ Offshore Leaks Database (CSV)

**Checks Performed**:
- Name matching in entities database
- Officer matching
- Jurisdiction analysis (tax havens)
- Incorporation/inactivation dates

**Red Flags**:
- Found in offshore leaks
- Tax haven jurisdiction
- Recently dissolved
- Circular ownership structures

**Output**:
```python
{
    'offshore_hits': int,
    'matches': [{
        'name': str,
        'jurisdiction': str,
        'source_investigation': str,  # 'Panama Papers', etc.
        'incorporation_date': str,
        'status': str
    }],
    'jurisdictions': [str],
    'red_flags': [str],
    'confidence': float
}
```

### 4. Trade Activity Module (`trade_checker.py`)

**Purpose**: Verify real business operations through trade data

**Data Sources**:
- UN Comtrade API (aggregate country/product level)
- Note: Company-level requires manual ImportYeti lookup

**Checks Performed**:
- Aggregate trade volume for claimed industry/country
- Industry-product code alignment
- Trade pattern anomalies

**Limitations**:
- Cannot directly verify company-level shipments
- Inference-based (if country has zero trade in claimed sector, flag)

**Red Flags**:
- Zero trade in claimed sector
- Country has no/minimal exports in industry
- Mismatch between business description and trade data

**Output**:
```python
{
    'has_trade_data': bool,
    'country_trade_volume': float,  # USD
    'industry_aligned': bool,
    'manual_check_needed': bool,
    'importyeti_url': str,  # For manual verification
    'red_flags': [str],
    'confidence': float
}
```

### 5. Risk Scoring Engine (`risk_scorer.py`)

**Purpose**: Aggregate findings into actionable risk score

**Scoring Algorithm**:

```python
# Base score starts at 50 (neutral)
base_score = 50

# Registry checks (max impact: ±25 points)
if registry.found and registry.status == 'active':
    score += 15
if registry.last_filing_date < 6 months ago:
    score += 10
if not registry.found:
    score -= 20
if registry.status in ['dissolved', 'struck_off']:
    score -= 15

# Sanctions checks (max impact: -50 points)
if sanctions.sanctions_hits > 0:
    score -= 30
if sanctions.pep_hits > 0:
    score -= 10

# Offshore checks (max impact: -20 points)
if offshore.offshore_hits > 0:
    score -= 15
if offshore.tax_haven:
    score -= 5

# Trade activity (max impact: ±15 points)
if trade.has_trade_data and trade.industry_aligned:
    score += 15
if trade.country_trade_volume == 0:
    score -= 10

# Normalize to 0-100
final_score = max(0, min(100, score))
```

**Risk Categories**:
- 70-100: Low Risk (Likely legitimate)
- 40-69: Medium Risk (Requires investigation)
- 0-39: High Risk (Shell company indicators)

**Output**:
```python
{
    'risk_score': int,  # 0-100
    'risk_level': str,  # 'LOW', 'MEDIUM', 'HIGH'
    'confidence': float,  # Overall confidence in assessment
    'critical_flags': [str],  # Major red flags
    'all_red_flags': [str],
    'recommendations': [str]
}
```

## Data Flow Sequence

1. **Input Validation**
   - Normalize company name
   - Validate country code (if provided)
   - Detect jurisdiction from name patterns

2. **Parallel Data Collection** (concurrent API calls)
   - Registry lookup (UK/US based on country)
   - Sanctions screening (both APIs)
   - Offline checks (ICIJ database)
   - Trade data query (UN Comtrade)

3. **Data Aggregation**
   - Merge results from all modules
   - Cross-reference findings (e.g., match officers across sources)
   - Resolve conflicts

4. **Risk Assessment**
   - Calculate base score
   - Apply weighted adjustments
   - Generate confidence intervals
   - Identify critical flags

5. **Report Generation**
   - Structure JSON output
   - Create human-readable summary
   - Include actionable next steps

## Implementation Strategy

### Phase 1: Core Infrastructure (This MVP)
- ✅ API client wrappers
- ✅ Data models
- ✅ Basic scoring
- ✅ CLI interface
- ✅ JSON output

### Phase 2: Enhancements (Future)
- Web UI (Streamlit/Flask)
- Batch processing
- Database caching
- Advanced ML scoring
- Report export (PDF/Excel)
- Webhook integrations

## Technology Stack

- **Language**: Python 3.8+
- **Core Libraries**:
  - `requests` - HTTP clients
  - `pandas` - CSV/data processing
  - `python-dotenv` - Environment management
  - `argparse` - CLI parsing
  - `concurrent.futures` - Parallel execution
- **Optional Libraries**:
  - `neo4j` - ICIJ graph database (advanced)
  - `streamlit` - Web UI (future)

## File Structure

```
trade/
├── company_verifier.py          # Main CLI entry point
├── config.py                    # Configuration and API keys
├── modules/
│   ├── __init__.py
│   ├── registry_checker.py      # UK/US registry APIs
│   ├── sanctions_checker.py     # OpenSanctions + ITA
│   ├── offshore_checker.py      # ICIJ database
│   ├── trade_checker.py         # UN Comtrade
│   └── risk_scorer.py           # Scoring engine
├── utils/
│   ├── __init__.py
│   ├── api_client.py            # Base API client with retry logic
│   ├── cache.py                 # Response caching
│   └── helpers.py               # Name normalization, etc.
├── data/
│   └── icij_offshore/           # Downloaded ICIJ CSVs
├── .env.example                 # Template for API keys
├── requirements.txt
├── API_DOCUMENTATION.md         # (Already created)
├── ARCHITECTURE.md              # (This file)
└── README.md                    # Usage guide
```

## Configuration Management

**Environment Variables** (stored in `.env`):
```bash
# OpenSanctions
OPENSANCTIONS_API_KEY=your_key_here

# Companies House UK
COMPANIES_HOUSE_API_KEY=your_key_here

# UN Comtrade
UN_COMTRADE_SUBSCRIPTION_KEY=your_key_here

# ITA Trade.gov
ITA_SUBSCRIPTION_KEY=your_key_here

# Data paths
ICIJ_DATA_PATH=/path/to/icij/csv/files

# Optional
USER_AGENT=CompanyVerifier/1.0 (your@email.com)
```

## Error Handling Strategy

1. **API Failures**
   - Graceful degradation (continue with available data)
   - Retry with exponential backoff (3 attempts)
   - Log failures for manual review
   - Mark confidence as reduced

2. **Rate Limiting**
   - Implement per-API rate limiters
   - Queue requests if limit approaching
   - Cache responses aggressively
   - Inform user of delays

3. **Data Quality**
   - Validate API responses
   - Handle missing fields gracefully
   - Flag low-confidence matches
   - Preserve raw data for audit

## Security Considerations

1. **API Keys**
   - Never commit to git
   - Use environment variables
   - Rotate regularly
   - Separate dev/prod keys

2. **Data Storage**
   - Don't persist PII unnecessarily
   - Encrypt cached data
   - Implement data retention policies
   - GDPR compliance for EU entities

3. **Usage Compliance**
   - Respect API ToS
   - Rate limit adherence
   - Attribution requirements
   - Commercial vs. non-commercial use

## Testing Strategy

**Test Cases**:

1. **Known Legitimate Company** (Apple Inc.)
   - Expected: Low risk, active registry, trade data
   - Score: 80+

2. **Known Shell Company** (Panama Papers entity)
   - Expected: High risk, offshore hits, no trade
   - Score: 0-30

3. **Edge Cases**:
   - Recently incorporated startup (legitimate but young)
   - Dormant holding company (legitimate but inactive)
   - Common name collisions

4. **API Failure Scenarios**:
   - Timeout handling
   - Invalid credentials
   - Rate limit exceeded
   - Malformed responses

## Deployment Considerations

### Local Development
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python company_verifier.py --name "Apple Inc." --country US
```

### Production (Future)
- Containerization (Docker)
- API gateway for web access
- Background job processing (Celery)
- Monitoring and alerting
- Load balancing

## Limitations and Disclaimers

1. **Not Legal Advice**: Tool provides risk indicators, not legal determinations
2. **False Positives**: Legitimate companies may score poorly (new startups, etc.)
3. **False Negatives**: Sophisticated shells may evade detection
4. **Data Lag**: APIs may have delayed updates
5. **Coverage**: Limited to UK/US registries + global sanctions
6. **Company-Level Trade**: Not fully automated (ImportYeti manual)

## Next Steps After MVP

1. **User Feedback**: Iterate on scoring weights
2. **Expand Coverage**: Add EU registries, more jurisdictions
3. **ML Enhancements**: Train classifier on labeled shell company data
4. **Automation**: Scrape ImportYeti or integrate paid API
5. **Reporting**: Generate detailed investigative reports
6. **Alerting**: Monitor company changes over time

---

**Version**: 1.0 MVP
**Last Updated**: 2026-01-21
