# Brave Search API Response Documentation

This document describes the structure and fields returned by the Brave Search API Web Search endpoint.

## Endpoint

```
GET https://api.search.brave.com/res/v1/web/search
```

## Authentication

```
Headers:
  X-Subscription-Token: <API_KEY>
  Accept: application/json
```

## Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query (required) |
| `count` | integer | Number of results (1-20, default 10) |
| `text_decorations` | boolean | Include text decorations (bold, etc.) |
| `safesearch` | string | "off", "moderate", or "strict" |
| `offset` | integer | Pagination offset |
| `country` | string | Country code for results |
| `freshness` | string | Filter by time: "pd" (day), "pw" (week), "pm" (month), "py" (year) |

---

## Response Structure

### Top-Level Fields

```json
{
  "query": { ... },      // Query metadata
  "mixed": { ... },      // Result ordering/mixing info
  "type": "search",      // Response type
  "web": { ... },        // Web search results (MAIN DATA)
  "videos": { ... },     // Video results (if any)
  "news": { ... },       // News results (if requested)
  "images": { ... }      // Image results (if requested)
}
```

---

## Query Object

Metadata about the search query.

```json
{
  "query": {
    "original": "Terraform Labs official website company",
    "show_strict_warning": false,
    "is_navigational": false,
    "is_news_breaking": false,
    "spellcheck_off": true,
    "country": "us",
    "bad_results": false,
    "should_fallback": false,
    "more_results_available": true,
    "postal_code": "",
    "city": "",
    "state": "",
    "header_country": ""
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `original` | string | The original search query |
| `is_navigational` | boolean | Query is looking for specific site |
| `is_news_breaking` | boolean | Query relates to breaking news |
| `spellcheck_off` | boolean | Spellcheck was disabled |
| `country` | string | Detected/specified country |
| `bad_results` | boolean | Search may have poor results |
| `should_fallback` | boolean | Should try alternative search |
| `more_results_available` | boolean | More pages available |

---

## Web Results Object

The main search results container.

```json
{
  "web": {
    "type": "search",
    "results": [ ... ],
    "family_friendly": true
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always "search" |
| `results` | array | Array of search result objects |
| `family_friendly` | boolean | Results are family-friendly |

---

## Individual Web Result Object

Each result in `web.results[]` has these fields:

```json
{
  "title": "Company Name | LinkedIn",
  "url": "https://linkedin.com/company/example",
  "is_source_local": false,
  "is_source_both": false,
  "description": "Company description from the page...",
  "page_age": "2023-07-21T16:33:10",
  "age": "July 21, 2023",
  "language": "en",
  "family_friendly": true,
  "type": "search_result",
  "subtype": "generic",
  "is_live": false,
  "profile": { ... },
  "meta_url": { ... },
  "thumbnail": { ... },
  "deep_results": { ... }
}
```

### Core Fields

| Field | Type | Description | Use for Scoring |
|-------|------|-------------|-----------------|
| `title` | string | Page title | Check for company name match |
| `url` | string | Full URL | Identify source type (social, news, gov) |
| `description` | string | Page snippet/meta description | Extract context, check for red flags |
| `page_age` | string | ISO 8601 timestamp | Determine content freshness |
| `age` | string | Human-readable age | Display purposes |
| `language` | string | ISO language code | Verify relevance |
| `family_friendly` | boolean | Safe for all audiences | N/A |

### Type Fields

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `type` | string | "search_result" | Result type |
| `subtype` | string | "generic", "faq", "article", "qa" | Content subtype |
| `is_live` | boolean | true/false | Live/dynamic content |
| `is_source_local` | boolean | true/false | Local business result |
| `is_source_both` | boolean | true/false | Mixed source type |

### Profile Object

Information about the source website.

```json
{
  "profile": {
    "name": "LinkedIn",
    "url": "https://sg.linkedin.com/company/terraform-labs",
    "long_name": "sg.linkedin.com",
    "img": "https://imgs.search.brave.com/..."
  }
}
```

| Field | Type | Description | Use for Scoring |
|-------|------|-------------|-----------------|
| `name` | string | Site/brand name | Identify authoritative sources |
| `url` | string | Profile URL | N/A |
| `long_name` | string | Full domain | Match against known domains |
| `img` | string | Favicon URL | N/A |

### Meta URL Object

Parsed URL components.

```json
{
  "meta_url": {
    "scheme": "https",
    "netloc": "linkedin.com",
    "hostname": "sg.linkedin.com",
    "favicon": "https://imgs.search.brave.com/...",
    "path": "› company › terraform-labs"
  }
}
```

| Field | Type | Description | Use for Scoring |
|-------|------|-------------|-----------------|
| `scheme` | string | "http" or "https" | Security indicator |
| `netloc` | string | Network location (domain) | Domain matching |
| `hostname` | string | Full hostname | Subdomain detection |
| `path` | string | Human-readable path | URL structure analysis |

### Thumbnail Object

Preview image information.

```json
{
  "thumbnail": {
    "src": "https://imgs.search.brave.com/...",
    "original": "https://media.licdn.com/...",
    "logo": true
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `src` | string | Brave-proxied thumbnail URL |
| `original` | string | Original image URL |
| `logo` | boolean | Image is a logo (not content image) |

### Deep Results Object

Additional structured data (e.g., Wikipedia sections).

```json
{
  "deep_results": {
    "buttons": [
      {
        "type": "button_result",
        "title": "History",
        "url": "https://en.wikipedia.org/wiki/Example#History"
      }
    ]
  }
}
```

---

## Videos Object

Video search results.

```json
{
  "videos": {
    "type": "videos",
    "results": [ ... ],
    "mutated_by_goggles": false
  }
}
```

### Video Result Object

```json
{
  "type": "video_result",
  "url": "https://www.youtube.com/watch?v=...",
  "title": "Video Title",
  "description": "Video description...",
  "age": "April 12, 2022",
  "page_age": "2022-04-12T19:45:27",
  "video": {
    "duration": "09:42",
    "creator": "Channel Name",
    "publisher": "YouTube"
  },
  "meta_url": { ... },
  "thumbnail": { ... }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `video.duration` | string | Video length (MM:SS) |
| `video.creator` | string | Channel/creator name |
| `video.publisher` | string | Platform (YouTube, Vimeo, etc.) |

---

## Mixed Object

Controls result ordering and SERP features.

```json
{
  "mixed": {
    "type": "mixed",
    "main": [
      { "type": "web", "index": 0, "all": false },
      { "type": "videos", "all": true },
      { "type": "web", "index": 1, "all": false }
    ],
    "top": [],
    "side": []
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `main` | array | Main result ordering |
| `top` | array | Top SERP features |
| `side` | array | Sidebar elements |

---

## Key Fields for Web Presence Scoring

### High-Value Indicators (Legitimate Company)

| What to Check | Where | Score Impact |
|---------------|-------|--------------|
| LinkedIn presence | `meta_url.netloc` contains "linkedin.com" | +1.0 |
| Wikipedia article | `meta_url.netloc` contains "wikipedia.org" | +1.5 |
| News coverage | `profile.name` in ["Reuters", "Bloomberg", "CNBC"] | +1.0 |
| Official website | URL matches company name pattern | +1.0 |
| Social media | Twitter/X, Facebook, Instagram URLs | +0.5 each |
| Crunchbase/PitchBook | Business database listings | +0.5 |
| High result count | `web.results.length` >= 10 | +0.5 |

### Red Flag Indicators (Shell Company Risk)

| What to Check | Where | Score Impact |
|---------------|-------|--------------|
| Low results | `web.results.length` < 3 | -1.5 |
| SEC.gov mentions | `url` or `description` contains "sec.gov" | -0.5 (investigate) |
| Fraud keywords | `description` contains ["fraud", "scam", "ponzi"] | -1.0 |
| Enforcement | `description` contains ["charged", "settlement", "penalty"] | -1.0 |
| Justice.gov | `url` contains "justice.gov" | -0.5 (investigate) |
| No social media | No LinkedIn/Twitter in top 10 | -0.5 |
| Only directory sites | All results from aggregators | -0.5 |

### Domain Categories

```python
AUTHORITATIVE_DOMAINS = {
    # Business Databases
    "linkedin.com": "social_business",
    "crunchbase.com": "business_db",
    "pitchbook.com": "business_db",
    "bloomberg.com": "financial_news",
    "reuters.com": "news",

    # Government/Regulatory
    "sec.gov": "regulatory",
    "justice.gov": "regulatory",
    "treasury.gov": "regulatory",

    # Reference
    "wikipedia.org": "reference",

    # Social Media
    "twitter.com": "social",
    "x.com": "social",
    "facebook.com": "social",

    # Crypto/Business News
    "coindesk.com": "industry_news",
    "cryptoslate.com": "industry_news",
}
```

---

## Example: Extracting Scoring Data

```python
def extract_presence_signals(brave_response: dict) -> dict:
    """Extract web presence scoring signals from Brave API response."""

    results = brave_response.get("web", {}).get("results", [])

    signals = {
        "total_results": len(results),
        "has_linkedin": False,
        "has_wikipedia": False,
        "has_twitter": False,
        "has_news_coverage": False,
        "has_business_db": False,
        "regulatory_mentions": [],
        "fraud_keywords_found": [],
        "official_website": None,
        "domains_found": set(),
    }

    NEWS_DOMAINS = ["reuters", "bloomberg", "cnbc", "wsj", "nytimes"]
    BUSINESS_DBS = ["crunchbase", "pitchbook", "golden.com", "rocketreach"]
    FRAUD_KEYWORDS = ["fraud", "scam", "ponzi", "charged", "settlement", "sec.gov"]

    for result in results:
        url = result.get("url", "").lower()
        description = result.get("description", "").lower()
        netloc = result.get("meta_url", {}).get("netloc", "")

        signals["domains_found"].add(netloc)

        # Check for key platforms
        if "linkedin.com" in url:
            signals["has_linkedin"] = True
        if "wikipedia.org" in url:
            signals["has_wikipedia"] = True
        if "twitter.com" in url or "x.com" in url:
            signals["has_twitter"] = True

        # News coverage
        if any(news in url for news in NEWS_DOMAINS):
            signals["has_news_coverage"] = True

        # Business databases
        if any(db in url for db in BUSINESS_DBS):
            signals["has_business_db"] = True

        # Red flags
        for keyword in FRAUD_KEYWORDS:
            if keyword in description:
                signals["fraud_keywords_found"].append(keyword)

        # Regulatory mentions
        if "sec.gov" in url or "justice.gov" in url:
            signals["regulatory_mentions"].append(url)

    signals["domains_found"] = list(signals["domains_found"])
    return signals
```

---

## Rate Limits

| Plan | Requests/Month | Rate Limit |
|------|----------------|------------|
| Free | 2,000 | 1 req/sec |
| Basic | 20,000 | 5 req/sec |
| Pro | Unlimited | 20 req/sec |

---

## Error Responses

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded"
  }
}
```

| Code | Description |
|------|-------------|
| 401 | Invalid API key |
| 429 | Rate limit exceeded |
| 500 | Server error |

---

## Sample Response Files

- `data/brave_api_response_example.json` - Full response for "Terraform Labs"
- `data/brave_api_response_shell_company.json` - Response for suspected shell company

---

## References

- [Brave Search API Documentation](https://api.search.brave.com/app/documentation/web-search/get-started)
- [Brave Search API Pricing](https://brave.com/search/api/)
