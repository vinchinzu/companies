#!/usr/bin/env python3
"""
Scrape SEC enforcement-related data via EDGAR Full-Text Search API.

This uses the publicly accessible SEC EDGAR search API to find:
- Companies with registration revoked
- Filings mentioning "SEC v." lawsuits
- Filings mentioning securities fraud
- Companies under enforcement actions

This API is different from the main SEC website and often has
different/lighter rate limiting.

Usage:
    python scrape_sec_edgar.py --output data/sec_enforcement.json
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict, field

import requests

# SEC requires declaring your traffic
USER_AGENT = "CompanyResearchTool/1.0 (Educational Research; contact@example.com)"

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}

BASE_URL = "https://efts.sec.gov/LATEST/search-index"


@dataclass
class EnforcementHit:
    """A company/filing found in enforcement-related search."""
    cik: str
    company_name: str
    form_type: str
    file_date: str
    search_type: str  # 'revoked', 'sec_v', 'fraud_mention', etc.
    sic_code: Optional[str] = None
    state: Optional[str] = None
    description: Optional[str] = None


class SECEdgarScraper:
    """Scrapes SEC EDGAR for enforcement-related data."""

    SEARCH_QUERIES = {
        "sec_v_cases": '%22SEC v.%22',  # Literal "SEC v."
        "securities_fraud": '%22securities fraud%22 AND %22complaint%22',
        "ponzi_scheme": '%22ponzi scheme%22',
        "investment_fraud": '%22investment fraud%22',
        "wire_fraud": '%22wire fraud%22',
        "unregistered_securities": '%22unregistered securities%22 OR %22unregistered offering%22',
        "enforcement_action": '%22SEC enforcement%22 OR %22enforcement action%22',
    }

    # Form types that indicate enforcement-related activity
    ENFORCEMENT_FORMS = ['REVOKED', 'AW', 'AW WD']

    def __init__(self, delay: float = 1.0):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay

    def search(
        self,
        query: str,
        start_date: str = "2020-01-01",
        end_date: str = None,
        size: int = 100,
        from_offset: int = 0,
    ) -> dict:
        """Execute a search query against EDGAR full-text search."""
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Build URL with query string directly (not using params for 'q')
        # The 'q' parameter needs to be URL-encoded properly
        url = f"{BASE_URL}?q={query}&dateRange=custom&startdt={start_date}&enddt={end_date}&from={from_offset}&size={size}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            time.sleep(self.delay)
            result = response.json()
            return result
        except requests.RequestException as e:
            print(f"  Search error: {e}")
            return {"hits": {"total": {"value": 0}, "hits": []}}
        except json.JSONDecodeError as e:
            print(f"  JSON decode error: {e}")
            return {"hits": {"total": {"value": 0}, "hits": []}}

    def search_revoked_registrations(
        self,
        start_date: str = "2020-01-01",
        end_date: str = None,
    ) -> list[EnforcementHit]:
        """Find companies whose SEC registration was revoked."""
        hits = []

        # Search for REVOKED form types
        result = self.search("*", start_date, end_date, size=500)

        for hit in result.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            form = src.get("form", "")

            if form in self.ENFORCEMENT_FORMS:
                ciks = src.get("ciks", [])
                names = src.get("display_names", [])

                for i, cik in enumerate(ciks):
                    name = names[i] if i < len(names) else f"CIK {cik}"
                    hits.append(EnforcementHit(
                        cik=cik,
                        company_name=name,
                        form_type=form,
                        file_date=src.get("file_date", ""),
                        search_type="revoked",
                        sic_code=src.get("sics", [""])[0] if src.get("sics") else None,
                        state=src.get("biz_states", [""])[0] if src.get("biz_states") else None,
                    ))

        return hits

    def search_enforcement_mentions(
        self,
        query_type: str,
        start_date: str = "2020-01-01",
        end_date: str = None,
        max_results: int = 500,
    ) -> list[EnforcementHit]:
        """Search for filings mentioning enforcement-related terms."""
        query = self.SEARCH_QUERIES.get(query_type)
        if not query:
            print(f"Unknown query type: {query_type}")
            return []

        hits = []
        offset = 0

        while offset < max_results:
            batch_size = min(100, max_results - offset)
            result = self.search(query, start_date, end_date, batch_size, offset)

            batch_hits = result.get("hits", {}).get("hits", [])
            if not batch_hits:
                break

            for hit in batch_hits:
                src = hit.get("_source", {})
                ciks = src.get("ciks", [])
                names = src.get("display_names", [])

                for i, cik in enumerate(ciks):
                    name = names[i] if i < len(names) else f"CIK {cik}"
                    hits.append(EnforcementHit(
                        cik=cik,
                        company_name=name,
                        form_type=src.get("form", ""),
                        file_date=src.get("file_date", ""),
                        search_type=query_type,
                        sic_code=src.get("sics", [""])[0] if src.get("sics") else None,
                        state=src.get("biz_states", [""])[0] if src.get("biz_states") else None,
                        description=src.get("file_description", ""),
                    ))

            offset += batch_size
            print(f"  Fetched {offset} results for {query_type}...")

        return hits

    def collect_all_enforcement_data(
        self,
        start_date: str = "2020-01-01",
        end_date: str = None,
    ) -> list[EnforcementHit]:
        """Collect enforcement data from all query types."""
        all_hits = []

        print("Searching for revoked registrations...")
        revoked = self.search_revoked_registrations(start_date, end_date)
        print(f"  Found {len(revoked)} revoked registrations")
        all_hits.extend(revoked)

        for query_type in self.SEARCH_QUERIES:
            print(f"\nSearching for {query_type}...")
            hits = self.search_enforcement_mentions(query_type, start_date, end_date)
            print(f"  Found {len(hits)} hits")
            all_hits.extend(hits)

        # Deduplicate by CIK
        seen_ciks = {}
        unique_hits = []
        for hit in all_hits:
            if hit.cik not in seen_ciks:
                seen_ciks[hit.cik] = hit
                unique_hits.append(hit)
            else:
                # Merge search types
                existing = seen_ciks[hit.cik]
                if hit.search_type not in existing.search_type:
                    existing.search_type = f"{existing.search_type},{hit.search_type}"

        return unique_hits


def main(output_path: str = "data/sec_enforcement.json", start_date: str = "2020-01-01"):
    """Main function to collect SEC enforcement data."""
    print("=" * 60)
    print("SEC EDGAR Enforcement Data Collector")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    scraper = SECEdgarScraper(delay=1.0)

    hits = scraper.collect_all_enforcement_data(start_date=start_date)

    print(f"\n{'=' * 60}")
    print(f"Total unique companies found: {len(hits)}")

    # Convert to dicts and save
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "collected_at": datetime.now().isoformat(),
        "start_date": start_date,
        "total_companies": len(hits),
        "companies": [asdict(h) for h in hits],
    }

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Saved to {output_file}")

    # Show summary by search type
    type_counts = {}
    for hit in hits:
        for t in hit.search_type.split(','):
            type_counts[t] = type_counts.get(t, 0) + 1

    print("\nBreakdown by search type:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/sec_enforcement.json")
    parser.add_argument("--start-date", default="2020-01-01")
    args = parser.parse_args()

    main(output_path=args.output, start_date=args.start_date)
