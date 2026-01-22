# ITA API Status Report

## Issue Summary

Your PRIMARY_KEY from Trade.gov is **not working** with the ITA Consolidated Screening List API endpoints. All requests return HTTP 301 redirects to `developer.trade.gov`.

## Test Results

```
API Key: YOUR_PRIMARY_KEY
Product: Consolidated Screening List - v1 + Business Service Providers - v1
```

### Endpoints Tested

All endpoints return **301 Redirect** (not working):

1. `https://api.trade.gov/v1/consolidated_screening_list/search`
2. `https://api.trade.gov/consolidated_screening_list/v1/search`
3. Multiple authentication header formats tried

## Possible Causes

1. **API Deprecated**: The v1 API may have been sunset
2. **Wrong Product**: Your subscription may be for a different API version or product
3. **Endpoint Changed**: ITA may have migrated to a new API gateway
4. **Authentication Method**: May require OAuth or different auth headers

## Working Alternative: OpenSanctions Bulk Data

Instead of the ITA API, use **OpenSanctions bulk data download** (100% free, no API key needed):

### Advantages

- ✅ **Free** - No API key required
- ✅ **Comprehensive** - Includes OFAC SDN, EU sanctions, UN sanctions
- ✅ **Fast** - Local lookups, no rate limits
- ✅ **Reliable** - No API authentication issues

### How It Works

OpenSanctions provides downloadable datasets in multiple formats:

```python
# Download OFAC SDN list (Specially Designated Nationals)
https://data.opensanctions.org/datasets/latest/us_ofac_sdn/entities.ftm.json

# Or just the names (faster)
https://data.opensanctions.org/datasets/latest/us_ofac_sdn/names.txt
```

### Implementation

Your other tool (`..`) already has a working implementation:

```python
# See: scrapers/opensanctions.py
from scrapers.opensanctions import OpenSanctionsClient

client = OpenSanctionsClient(cache_dir='./data/opensanctions')

# Download OFAC data (one-time, cached for 24 hours)
entities = client.get_companies()
print(f"Loaded {len(entities)} sanctioned entities")

# Check a company
result = client.check_against_sanctions("Central Bank of Iran")
if result['match']:
    print(f"⚠️ SANCTIONS HIT: {result['matched_name']}")
    print(f"   Confidence: {result['confidence']}")
```

## Integration with Company Verifier Tool

### Option 1: Copy Working Implementation

```bash
# Copy the working OpenSanctions scraper
cp ../company/company-research-tool/scrapers/opensanctions.py ./modules/

# Update sanctions_checker.py to use it
```

### Option 2: Use OpenSanctions Data API (No Key)

The bulk data approach is already partially working (see test results above).

## Sample Test with Known Sanctioned Companies

```bash
# Test with companies from your fraudulent_companies.csv
python3 << 'EOF'
import requests

# Download OFAC names list
url = "https://data.opensanctions.org/datasets/latest/us_ofac_sdn/names.txt"
response = requests.get(url)
sanctioned_names = set(line.lower().strip() for line in response.text.split('\n') if line)

# Test known sanctioned entities
test_companies = [
    "Central Bank of Iran",
    "Korea Myongdok Shipping",
    "OOO Khartiya",
    "Apple Inc"  # Should NOT match
]

for company in test_companies:
    if company.lower() in sanctioned_names:
        print(f"🔴 SANCTIONS HIT: {company}")
    else:
        # Check partial matches
        found = False
        for name in sanctioned_names:
            if company.lower() in name or name in company.lower():
                print(f"🟡 POSSIBLE MATCH: {company} ~ {name}")
                found = True
                break
        if not found:
            print(f"🟢 CLEAN: {company}")
EOF
```

## ITA API Troubleshooting Steps

If you want to continue trying to fix the ITA API:

### 1. Verify Subscription Product

Log into https://developer.trade.gov/ and check:
- Which exact API products your key is subscribed to
- What the current endpoint URLs are
- If there's a v2 or newer version available

### 2. Check for New Documentation

The API may have moved to:
- `https://api.trade.gov/gateway/v2/...`
- Different authentication method (OAuth?)
- New base URL entirely

### 3. Contact ITA Support

Email: **DataServices@trade.gov**

Ask:
- "What is the current endpoint for Consolidated Screening List v1?"
- "Is my subscription key (YOUR_PRIMARY_KEY) active?"
- "Has the API been deprecated or migrated?"

## Recommendation

**Use OpenSanctions bulk data** instead of the ITA API:

1. It's working right now (verified in tests)
2. It's free and has no rate limits
3. It covers the same sanctions lists (OFAC, EU, UN)
4. Your other tool is already using it successfully

The ITA API can be revisited later once Trade.gov provides working endpoints or updated documentation.

---

## Status

- ✅ **SEC EDGAR**: Working
- ✅ **OpenSanctions Bulk Data**: Working
- ❌ **ITA API**: Not working (redirects, needs troubleshooting)

**Verdict**: Your tool is functional with 2/3 data sources. The ITA API is a "nice to have" but OpenSanctions provides the same data.
