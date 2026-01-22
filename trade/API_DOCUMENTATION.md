# Company Verification and Shell Company Detection APIs

Comprehensive documentation of free/open APIs and data sources for automated company verification and shell company detection using Python.

---

## 1. OpenSanctions API

### Overview
OpenSanctions provides sanctions data, politically exposed persons (PEPs), and persons of interest for compliance screening and due diligence.

### API Endpoint
- **Base URL**: `https://api.opensanctions.org`
- **API Documentation**: https://api.opensanctions.org/docs
- **OpenAPI Spec**: https://api.opensanctions.org/openapi.json

### Key Endpoints
- `/match` - Fuzzy matching of entities against sanctions lists
- `/search` - Full-text search with filters
- `/entities/{id}` - Retrieve specific entity by ID

### Authentication
- **Method**: API Key (Authorization header)
- **Registration**: https://www.opensanctions.org/api/
- **Format**: `Authorization: ApiKey YOUR_API_KEY`

### Rate Limits & Pricing
- **Free Tier**: Available for non-commercial users (media, NGOs, researchers)
- **Commercial**: €0.10 per successful API call
- **Volume Pricing**: Available above 20,000 requests/month
- **Quota Enforcement**: 429 HTTP status when exceeded
- **Trial**: Free trial keys available for business email signups

### Example Python Usage
```python
import requests

API_KEY = "your_api_key"
BASE_URL = "https://api.opensanctions.org"

headers = {
    "Authorization": f"ApiKey {API_KEY}"
}

# Match endpoint - fuzzy name matching
response = requests.get(
    f"{BASE_URL}/match/default",
    headers=headers,
    params={
        "schema": "Company",
        "properties.name": "Company Name Ltd"
    }
)

# Search endpoint
response = requests.get(
    f"{BASE_URL}/search/default",
    headers=headers,
    params={
        "q": "search term",
        "limit": 10
    }
)
```

### Data Fields Returned
- Entity name and aliases (alt_names)
- Schema type (Person, Company, Organization)
- Countries, nationalities
- Dates of birth (for persons)
- Associated sanctions programs
- Source datasets
- Relationships to other entities
- Remarks and additional context

### Automation Notes
- OAuth2 authentication supported
- Can be queried with standard HTTP clients (requests, httpx)
- Example code available: https://github.com/opensanctions/api-examples
- Supports bulk matching operations
- Reconciliation API spec compatible

---

## 2. UN Comtrade API

### Overview
Country-level international trade statistics (NOT company-level). Useful for verifying trade patterns and volumes at the national level.

### API Endpoint
- **Base URL**: `https://comtradeplus.un.org/`
- **Developer Portal**: https://comtradedeveloper.un.org/
- **API Documentation**: Available after registration

### Authentication
- **Method**: Subscription Key
- **Registration**: Required at UN Comtrade Developer Portal
- **Process**: Sign up → Select "comtrade - v1" (free product) → Subscribe → Get API key

### Rate Limits
- **With Token**: 500 calls/day, up to 100,000 records per call
- **Request Limit**: Check API documentation for per-minute limits
- **Legacy Limits**: 1 request/second, 10,000 requests/hour (older API versions)

### Example Python Usage
```python
import comtradeapicall

# Official Python package
mydf = comtradeapicall.getFinalData(
    subscription_key="YOUR_KEY",
    typeCode='C',           # Commodity
    freqCode='M',           # Monthly
    clCode='HS',            # Harmonized System
    period='202205',        # YYYYMM
    reporterCode='36',      # Country code (36 = Australia)
    cmdCode='91,90',        # Commodity codes
    flowCode='M',           # Import
    partnerCode=None,       # All partners
    partner2Code=None,
    customsCode=None,
    motCode=None,
    maxRecords=2500,
    format_output='JSON',
    aggregateBy=None,
    breakdownMode='classic',
    countOnly=None,
    includeDesc=True
)
```

### Data Fields Returned
- Trade flow (imports/exports)
- Reporter and partner countries
- Commodity codes (HS classification)
- Trade values (USD)
- Quantity measures
- Period (yearly, monthly)
- Customs procedures

### Automation Notes
- **Python Package**: `comtradeapicall` (GitHub: uncomtrade/comtradeapicall)
- **R Package**: `comtradr` (for R users)
- Maximum 12-year interval per request
- Country names must be in ISO3 format
- **LIMITATION**: Country-level only, not company-specific

---

## 3. UK Companies House API

### Overview
Real-time access to UK company registration data, officers, filing history, and persons with significant control (PSC).

### API Endpoint
- **Base URL**: `https://api.companieshouse.gov.uk`
- **Developer Portal**: https://developer.company-information.service.gov.uk/
- **API Specs**: https://developer-specs.company-information.service.gov.uk/

### Key Endpoints
```
GET /company/{company_number}                    # Company profile
GET /company/{company_number}/officers           # Officers list
GET /company/{company_number}/filing-history     # Filing history
GET /company/{company_number}/persons-with-significant-control
GET /search/companies                            # Search companies
```

### Authentication
- **Method**: Basic HTTP Authentication (API key as username, empty password)
- **Registration**: Required - Create account at Companies House
- **Format**: `Authorization: Basic base64(api_key:)`

### Rate Limits
- **Limit**: 600 requests per 5 minutes
- **Enforcement**: 429 Too Many Requests when exceeded
- **Reset**: Automatic after 5 minutes
- **Best Practice**: 0.5 seconds between requests (120/minute = safe limit)

### Example Python Usage
```python
import requests
from requests.auth import HTTPBasicAuth

API_KEY = "your_api_key"
BASE_URL = "https://api.companieshouse.gov.uk"

# Company profile
company_number = "00000006"  # Example: Marks & Spencer
response = requests.get(
    f"{BASE_URL}/company/{company_number}",
    auth=HTTPBasicAuth(API_KEY, '')
)

# Officers
response = requests.get(
    f"{BASE_URL}/company/{company_number}/officers",
    auth=HTTPBasicAuth(API_KEY, '')
)

# Filing history
response = requests.get(
    f"{BASE_URL}/company/{company_number}/filing-history",
    auth=HTTPBasicAuth(API_KEY, '')
)

# Search
response = requests.get(
    f"{BASE_URL}/search/companies",
    auth=HTTPBasicAuth(API_KEY, ''),
    params={"q": "company name", "items_per_page": 20}
)
```

### Data Fields Returned

**Company Profile:**
- company_name, company_number, company_status
- type, jurisdiction, date_of_creation
- registered_office_address
- accounts (next_due, last_made)
- confirmation_statement
- sic_codes (industry classification)
- has_insolvency_history, has_charges

**Officers:**
- name, officer_role, appointed_on, resigned_on
- nationality, country_of_residence, occupation
- date_of_birth (month/year)
- address

**Filing History:**
- category, date, description, type
- barcode, transaction_id
- links to document downloads

**PSC (Persons with Significant Control):**
- name, kind, nationality
- nature_of_control
- notified_on, ceased_on

### Automation Notes
- Free API, no usage fees
- Live, real-time data
- RESTful design
- Comprehensive documentation with interactive explorer
- Rate limiting requires careful throttling
- Python implementation examples: GitHub MarckK/companies-house-api

---

## 4. SEC EDGAR API

### Overview
Free access to US company filings (10-K, 10-Q, 8-K, etc.) and financial data in JSON format. No authentication required.

### API Endpoint
- **Base URL**: `https://data.sec.gov`
- **Main Documentation**: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- **Data Portal**: https://data.sec.gov/

### Key Endpoints
```
# Submissions (Filing history)
https://data.sec.gov/submissions/CIK{10-digit-CIK}.json

# Company Facts (XBRL financial data)
https://data.sec.gov/api/xbrl/companyfacts/CIK{10-digit-CIK}.json

# XBRL Frames (aggregated data across companies)
https://data.sec.gov/api/xbrl/frames/us-gaap/{taxonomy}/{unit}/{period}.json

# Bulk Downloads
https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip
https://www.sec.gov/Archives/edgar/daily-index/bulkdata/companyfacts.zip
```

### Authentication
- **Method**: None required
- **User-Agent**: REQUIRED - must declare identity
- **Format**: `User-Agent: Company Name contact@company.com`

### Rate Limits
- **Limit**: 10 requests per second
- **Enforcement**: IP-based blocking for 10 minutes if exceeded
- **Fair Access**: SEC requires efficient scripting and reasonable use
- **Best Practice**: 5-7 requests/second for large downloads

### Example Python Usage
```python
import requests
import time

headers = {
    "User-Agent": "MyCompany admin@mycompany.com"
}

# Get company submissions (filing history)
cik = "0000320193"  # Apple Inc. (must be 10 digits with leading zeros)
response = requests.get(
    f"https://data.sec.gov/submissions/CIK{cik}.json",
    headers=headers
)
data = response.json()

# Get company facts (XBRL financial data)
response = requests.get(
    f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
    headers=headers
)
facts = response.json()

# Rate limiting example
def get_sec_data(cik):
    time.sleep(0.15)  # 6-7 requests/second
    response = requests.get(
        f"https://data.sec.gov/submissions/CIK{cik}.json",
        headers=headers
    )
    return response.json()
```

### Data Fields Returned

**Submissions API:**
- cik, entityType, name, tickers, exchanges
- sic, sicDescription (industry classification)
- filings.recent (arrays):
  - accessionNumber, filingDate, reportDate
  - primaryDocument, primaryDocUrl
  - form (10-K, 10-Q, 8-K, etc.)
  - items, size, isXBRL, isInlineXBRL

**Company Facts API:**
- entityName, cik
- facts (organized by taxonomy):
  - us-gaap (US GAAP items)
  - dei (Document Entity Information)
  - Each fact contains:
    - label, description, units
    - Historical values by filing

### Automation Notes
- Python package: `sec-edgar-api` (PyPI)
- Features auto rate-limiting (10 req/sec)
- Bulk downloads updated nightly at 3:00 AM ET
- Processing delay: <1 second for submissions, <1 minute for XBRL
- No API key registration needed
- Must include User-Agent header or requests will be rejected

---

## 5. ICIJ Offshore Leaks Database

### Overview
Database of offshore entities from major leak investigations (Panama Papers, Pandora Papers, Paradise Papers, etc.). 810,000+ offshore entities.

### Download URLs
- **CSV Format (Full Database)**:
  ```
  https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip
  ```

- **Neo4j Graph Database**:
  ```
  # Neo4j 4.x
  https://offshoreleaks-data.icij.org/offshoreleaks/neo4j/icij-offshoreleaks-4.4.26.dump

  # Neo4j 5.x
  https://offshoreleaks-data.icij.org/offshoreleaks/neo4j/icij-offshoreleaks-5.13.0.dump
  ```

- **Download Page**: https://offshoreleaks.icij.org/pages/database

### Data Format

**CSV Files (in ZIP archive):**
- Separate CSV files for each node type:
  - `nodes-addresses.csv`
  - `nodes-entities.csv`
  - `nodes-intermediaries.csv`
  - `nodes-officers.csv`
- One CSV for all relationships:
  - `relationships.csv`

**Neo4j Format:**
- Graph database dump files
- Load into Neo4j Desktop or Neo4j AuraDB
- Query using Cypher language

### Authentication
- **None required** - Open data
- **License**: Open Database License (ODbL)
- **Content License**: Creative Commons Attribution-ShareAlike

### Example Python Usage

**CSV Approach:**
```python
import pandas as pd
import zipfile
import requests

# Download and extract
url = "https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip"
response = requests.get(url)

with open('offshore_leaks.zip', 'wb') as f:
    f.write(response.content)

# Extract and load
with zipfile.ZipFile('offshore_leaks.zip', 'r') as zip_ref:
    zip_ref.extractall('offshore_data')

# Load entities
entities = pd.read_csv('offshore_data/nodes-entities.csv')
officers = pd.read_csv('offshore_data/nodes-officers.csv')
relationships = pd.read_csv('offshore_data/relationships.csv')

# Search for company
company_matches = entities[entities['name'].str.contains('Company Name', case=False, na=False)]
```

**Neo4j Approach (requires neo4j Python driver):**
```python
from neo4j import GraphDatabase

uri = "neo4j://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "password"))

def find_entity(tx, name):
    query = """
    MATCH (e:Entity)
    WHERE e.name CONTAINS $name
    RETURN e
    """
    result = tx.run(query, name=name)
    return [record["e"] for record in result]

with driver.session() as session:
    results = session.read_transaction(find_entity, "Company Name")
```

### Data Fields Available

**Entities (Companies, Trusts):**
- node_id, name, original_name
- jurisdiction, jurisdiction_description
- service_provider, country_codes
- countries, incorporation_date, inactivation_date
- struck_off_date, closed_date
- sourceID (which leak investigation)
- valid_until, note

**Officers (Individuals):**
- node_id, name
- countries, country_codes
- valid_until, sourceID

**Intermediaries (Law firms, banks):**
- node_id, name
- country_codes, countries
- status, sourceID

**Relationships:**
- rel_type (e.g., "officer_of", "intermediary_of", "connected_to")
- node_1 (source node_id)
- node_2 (target node_id)
- link, start_date, end_date
- sourceID

### Automation Notes
- Large file size (several GB compressed)
- Updated periodically with new investigations
- GitHub repo: https://github.com/ICIJ/offshoreleaks-data-packages
- Can combine with other data sources using company names/addresses
- Web interface available: https://offshoreleaks.icij.org/ for manual searches
- Best for batch analysis, not real-time queries

---

## 6. ImportYeti

### Overview
US import/export data showing supplier-buyer relationships based on customs data (bills of lading). Useful for verifying actual business activity.

### Access Methods

**Web Interface (Free):**
- **URL**: https://www.importyeti.com/
- **Access**: Free, no signup required
- **Features**: Search by company name, view suppliers/buyers

**Official API:**
- **URL**: https://data.importyeti.com/
- **Status**: BETA
- **Access**: Must request access via questionnaire
- **Cost**: May require payment (not guaranteed free)

**Third-Party Scraper API:**
- **Platform**: Apify
- **URL**: https://apify.com/parseforge/importyeti-scraper
- **Access**: Requires Apify account and API token
- **Cost**: Apify usage-based pricing

### Rate Limits
- **Official API**: Not publicly documented (requires application)
- **Web Interface**: No documented limits for manual use
- **Apify Scraper**: Subject to Apify platform limits

### Example Python Usage

**Web Scraping (Educational purposes - check ToS):**
```python
import requests
from bs4 import BeautifulSoup

# Note: Check ImportYeti's ToS before scraping
# This is for educational purposes only

company_name = "company-name"
url = f"https://www.importyeti.com/company/{company_name}"

response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
# Parse the HTML to extract supplier/buyer information
```

**Apify API Approach:**
```python
from apify_client import ApifyClient

client = ApifyClient("YOUR_APIFY_TOKEN")

# Prepare the Actor input
run_input = {
    "companyName": "Company Name",
    "maxResults": 100
}

# Run the Actor and wait for it to finish
run = client.actor("parseforge/importyeti-scraper").call(run_input=run_input)

# Fetch results
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(item)
```

### Data Fields Available
- Company name (importer/exporter)
- Supplier/buyer relationships
- Product descriptions
- Shipment dates
- Container counts
- Weight/quantity
- Port of origin
- Port of destination
- Country of origin

### Automation Notes
- **FREE**: Web interface remains free without subscription
- **API Access**: Requires application and possible payment
- **Data Coverage**: US import data (customs records)
- **Alternative**: Can request official API access via form at data.importyeti.com
- **Use Case**: Verify if a company has actual trade activity
- **Limitation**: US-centric data, may miss non-US trade

---

## 7. ITA Trade.gov APIs

### Overview
International Trade Administration APIs providing trade data, screening lists, market research, and trade leads.

### API Endpoint
- **Base URL**: `https://api.trade.gov`
- **Developer Portal**: https://developer.trade.gov/
- **API List**: https://developer.trade.gov/apis

### Key APIs Available

**1. Consolidated Screening List (CSL) API**
- **Purpose**: Screen against 11 export control and sanctions lists
- **Lists Include**:
  - BIS Denied Persons List (DPL)
  - BIS Entity List (EL)
  - BIS Unverified List (UVL)
  - State Dept ITAR Debarred
  - State Dept Nonproliferation Sanctions
  - Treasury OFAC SDN (Specially Designated Nationals)
  - Treasury OFAC FSE (Foreign Sanctions Evaders)
  - And 4 more Treasury lists

**2. Trade Leads API**
- **Purpose**: Contract opportunities for US exporters
- **Sources**: State Dept BIDS, SAM, USTDA

**3. Market Intelligence API**
- **Purpose**: Market research and trade opportunities

### Authentication
- **Method**: Subscription Key
- **Registration**: https://developer.trade.gov/ (Sign In → Create Account)
- **Process**:
  1. Go to Products page
  2. Click "Data Services Platform APIs"
  3. Fill subscription name
  4. Press Subscribe
  5. Get primary/secondary keys from Profile page

### Rate Limits
- Not publicly documented
- Contact DataServices@trade.gov for details

### Example Python Usage

**Consolidated Screening List:**
```python
import requests

API_KEY = "your_subscription_key"
BASE_URL = "https://api.trade.gov"

headers = {
    "subscription-key": API_KEY
}

# Search screening lists
response = requests.get(
    f"{BASE_URL}/v1/consolidated_screening_list/search",
    headers=headers,
    params={
        "name": "Company Name",
        "fuzzy_name": "true",
        "size": 10
    }
)

results = response.json()

# Check if company is on any sanctions list
if results['total'] > 0:
    for hit in results['results']:
        print(f"Match: {hit['name']}")
        print(f"List: {hit['source']}")
        print(f"Programs: {hit.get('programs', [])}")
```

**Trade Leads:**
```python
# Search for trade opportunities
response = requests.get(
    f"{BASE_URL}/v2/trade_leads/search",
    headers=headers,
    params={
        "countries": "BR",  # Brazil
        "industries": "automotive",
        "size": 20
    }
)

leads = response.json()
```

### Data Fields Returned

**Consolidated Screening List:**
- name, alt_names (alternative names)
- type (Individual, Entity)
- programs (sanctions programs)
- title, remarks
- source (which list: DPL, SDN, etc.)
- source_list_url
- source_information_url
- addresses (street, city, country, postal_code)
- nationalities, citizenships
- dates_of_birth
- places_of_birth
- start_date, end_date

**Trade Leads:**
- title, description
- reference_number
- country, specific_location
- publish_date, end_date
- industry, project_size
- contact_information
- source (BIDS, SAM, USTDA)
- urls

### Automation Notes
- **Free Tier**: Yes - free subscription available
- **Data Policy**: No restrictions on use
- **Updates**: APIs continually updated
- **Support**: DataServices@trade.gov
- **Python Libraries**: None official, use requests
- **Use Case**: Compliance screening, finding trade opportunities
- **Fuzzy Matching**: CSL supports fuzzy name search

---

## Summary Comparison Table

| API | Authentication | Rate Limit | Free Tier | Best For |
|-----|---------------|------------|-----------|----------|
| OpenSanctions | API Key | Quota-based | Non-commercial only | Sanctions/PEP screening |
| UN Comtrade | Subscription Key | 500/day | Yes | Country trade statistics |
| Companies House | Basic Auth | 600/5min | Yes | UK company verification |
| SEC EDGAR | User-Agent only | 10/sec | Yes | US company filings |
| ICIJ Offshore Leaks | None (download) | N/A | Yes | Offshore entity detection |
| ImportYeti | Request-based | Unknown | Web only | Supplier verification |
| ITA Trade.gov | Subscription Key | Not disclosed | Yes | Sanctions screening, trade data |

---

## Python Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install required packages
pip install requests pandas neo4j beautifulsoup4 apify-client

# For UN Comtrade
pip install comtradeapicall

# For SEC EDGAR (with auto rate-limiting)
pip install sec-edgar-api
```

---

## Best Practices for Automation

1. **Rate Limiting**
   - Implement exponential backoff for 429 errors
   - Use time.sleep() between requests
   - Track request counts per time window

2. **Error Handling**
   - Catch HTTP errors (4xx, 5xx)
   - Retry with exponential backoff
   - Log failed requests for manual review

3. **User-Agent Headers**
   - Always include contact information
   - Use descriptive application names
   - Required for SEC, recommended for all

4. **API Keys**
   - Store in environment variables
   - Never commit to version control
   - Use separate keys for dev/prod

5. **Data Storage**
   - Cache responses to minimize API calls
   - Store raw JSON for reprocessing
   - Use databases for relationship data

6. **Compliance**
   - Review each API's Terms of Service
   - Respect rate limits and fair use policies
   - Attribute data sources appropriately

---

## Sources

- [OpenSanctions API Documentation](https://api.opensanctions.org/)
- [OpenSanctions API Guide](https://www.opensanctions.org/api/)
- [UN Comtrade Developer Portal](https://comtradedeveloper.un.org/)
- [UN Comtrade API Documentation](https://comtradeplus.un.org/)
- [Companies House API Overview](https://developer.company-information.service.gov.uk/overview)
- [Companies House API Specifications](https://developer-specs.company-information.service.gov.uk/)
- [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [ICIJ Offshore Leaks Database](https://offshoreleaks.icij.org/pages/database)
- [ImportYeti API](https://data.importyeti.com/)
- [ITA Data Services Platform](https://developer.trade.gov/)
- [Consolidated Screening List API](https://developer.trade.gov/consolidated-screening-list)
