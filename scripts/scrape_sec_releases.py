#!/usr/bin/env python3
"""
Scrape SEC Litigation Releases from the SEC website.

This script follows SEC.gov guidelines:
- Declares user agent with contact info
- Respects rate limits (max 10 req/sec, we use much slower)
- Saves HTML and extracts structured data

Usage:
    python scrape_sec_releases.py --pages 10 --delay 5

For overnight scraping:
    nohup python scrape_sec_releases.py --pages 100 --delay 10 > scrape.log 2>&1 &
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

import requests
from bs4 import BeautifulSoup

# SEC requires declaring your traffic with company info
# Update this with your actual contact info for production use
USER_AGENT = "CompanyResearchTool/1.0 (Educational/Research; contact@example.com)"

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# SEC litigation releases URL (new format)
BASE_URL = "https://www.sec.gov/enforcement-litigation/litigation-releases"
# Alternative old format
OLD_BASE_URL = "https://www.sec.gov/litigation/litreleases.htm"


@dataclass
class LitigationRelease:
    """Structured litigation release data."""
    release_number: str
    title: str
    date: str
    url: str
    description: Optional[str] = None
    complaint_url: Optional[str] = None
    defendants: list = None

    def __post_init__(self):
        if self.defendants is None:
            self.defendants = []


class SECLitReleaseScraper:
    """Scrapes SEC Litigation Releases."""

    def __init__(self, output_dir: str = "data/sec_releases"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch_page(self, url: str, delay: float = 2.0) -> Optional[str]:
        """Fetch a page with rate limiting."""
        try:
            response = self.session.get(url, timeout=30)

            if response.status_code == 403:
                print(f"  Rate limited or blocked (403)")
                return None

            response.raise_for_status()
            time.sleep(delay)
            return response.text

        except requests.RequestException as e:
            print(f"  Error fetching {url}: {e}")
            return None

    def parse_release_list_page(self, html: str) -> list[dict]:
        """Parse a page listing litigation releases."""
        releases = []
        soup = BeautifulSoup(html, 'lxml')

        # Try different selectors based on page structure
        # New SEC site structure
        items = soup.select('div.views-row, tr.views-row, article.node')

        if not items:
            # Try table rows
            items = soup.select('table tr')

        if not items:
            # Try list items
            items = soup.select('ul.list li, div.item')

        for item in items:
            try:
                # Extract link
                link = item.select_one('a[href*="litigation"], a[href*="litreleases"]')
                if not link:
                    continue

                title = link.get_text(strip=True)
                href = link.get('href', '')

                # Make URL absolute
                if href.startswith('/'):
                    href = f"https://www.sec.gov{href}"

                # Extract date
                date_elem = item.select_one('time, .date, td:nth-child(2)')
                date_str = date_elem.get_text(strip=True) if date_elem else ""

                # Extract release number (e.g., LR-12345)
                release_num = ""
                num_match = re.search(r'LR-?\d+', title) or re.search(r'LR-?\d+', href)
                if num_match:
                    release_num = num_match.group()

                releases.append({
                    'release_number': release_num,
                    'title': title,
                    'date': date_str,
                    'url': href,
                })

            except Exception as e:
                continue

        return releases

    def parse_release_detail(self, html: str, url: str) -> LitigationRelease:
        """Parse a single litigation release page for details."""
        soup = BeautifulSoup(html, 'lxml')

        # Extract title
        title_elem = soup.select_one('h1, .page-title, title')
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Extract release number
        release_num = ""
        num_match = re.search(r'LR-?\d+', title) or re.search(r'LR-?\d+', url)
        if num_match:
            release_num = num_match.group()

        # Extract date
        date_str = ""
        date_elem = soup.select_one('time, .date, .field-date')
        if date_elem:
            date_str = date_elem.get_text(strip=True)
        else:
            # Try to find date in text
            date_match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', str(soup))
            if date_match:
                date_str = date_match.group()

        # Extract main content/description
        content_elem = soup.select_one('.field-body, .node-content, article, #content')
        description = content_elem.get_text(strip=True)[:2000] if content_elem else ""

        # Find complaint PDF links
        complaint_url = None
        pdf_links = soup.select('a[href*=".pdf"]')
        for link in pdf_links:
            href = link.get('href', '')
            if 'comp' in href.lower() or 'complaint' in href.lower():
                if href.startswith('/'):
                    href = f"https://www.sec.gov{href}"
                complaint_url = href
                break

        # Extract defendant names from content
        defendants = []
        # Look for patterns like "SEC v. Company Name" or "charged Company Name"
        text = str(soup)
        defendant_patterns = [
            r'SEC\s+v\.\s+([A-Z][A-Za-z0-9\s,\.&]+?)(?:,|\.|;|$)',
            r'charged\s+([A-Z][A-Za-z0-9\s,\.&]+?)(?:\s+with|\s+for|,)',
            r'against\s+([A-Z][A-Za-z0-9\s,\.&]+?)(?:\s+for|\s+in|,)',
        ]
        for pattern in defendant_patterns:
            matches = re.findall(pattern, text[:5000])
            defendants.extend([m.strip() for m in matches if len(m.strip()) > 3])

        # Deduplicate
        defendants = list(dict.fromkeys(defendants))[:10]

        return LitigationRelease(
            release_number=release_num,
            title=title,
            date=date_str,
            url=url,
            description=description,
            complaint_url=complaint_url,
            defendants=defendants,
        )

    def scrape_list_pages(self, max_pages: int = 10, delay: float = 5.0) -> list[dict]:
        """Scrape multiple pages of litigation release listings."""
        all_releases = []

        for page_num in range(max_pages):
            url = f"{BASE_URL}?page={page_num}"
            print(f"Fetching page {page_num + 1}/{max_pages}: {url}")

            html = self.fetch_page(url, delay)
            if not html:
                print(f"  Failed to fetch page {page_num}")
                # Wait longer on failure
                time.sleep(delay * 3)
                continue

            # Save raw HTML
            html_path = self.output_dir / f"page_{page_num:03d}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)

            # Parse releases
            releases = self.parse_release_list_page(html)
            print(f"  Found {len(releases)} releases")

            if not releases:
                print("  No releases found, may have reached end")
                break

            all_releases.extend(releases)

            # Be nice to SEC servers
            time.sleep(delay)

        return all_releases

    def scrape_release_details(self, releases: list[dict], delay: float = 5.0) -> list[LitigationRelease]:
        """Scrape detailed info for each release."""
        detailed = []

        for i, release in enumerate(releases):
            url = release.get('url', '')
            if not url:
                continue

            print(f"[{i+1}/{len(releases)}] Fetching: {release.get('release_number', url[:50])}")

            html = self.fetch_page(url, delay)
            if not html:
                continue

            try:
                detail = self.parse_release_detail(html, url)
                detailed.append(detail)

                # Save individual release HTML
                if detail.release_number:
                    html_path = self.output_dir / f"{detail.release_number}.html"
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(html)

            except Exception as e:
                print(f"  Error parsing: {e}")
                continue

        return detailed

    def save_releases(self, releases: list, filename: str = "litigation_releases.json"):
        """Save releases to JSON."""
        filepath = self.output_dir / filename

        # Convert to dicts
        data = [asdict(r) if hasattr(r, '__dataclass_fields__') else r for r in releases]

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        print(f"Saved {len(releases)} releases to {filepath}")
        return filepath


def main(max_pages: int = 10, delay: float = 5.0, fetch_details: bool = False):
    """Main scraping function."""
    print("=" * 60)
    print("SEC Litigation Release Scraper")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"Max pages: {max_pages}")
    print(f"Delay: {delay}s between requests")
    print(f"User-Agent: {USER_AGENT}")
    print("=" * 60)
    print()

    scraper = SECLitReleaseScraper()

    # Scrape list pages
    print("Phase 1: Scraping release listings...")
    releases = scraper.scrape_list_pages(max_pages, delay)
    print(f"\nFound {len(releases)} total releases")

    if not releases:
        print("No releases found. May be rate limited.")
        return

    # Save basic list
    scraper.save_releases(releases, "releases_list.json")

    # Optionally fetch details
    if fetch_details:
        print("\nPhase 2: Fetching release details...")
        detailed = scraper.scrape_release_details(releases, delay)
        scraper.save_releases(detailed, "releases_detailed.json")

    print("\n" + "=" * 60)
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scrape SEC Litigation Releases")
    parser.add_argument("--pages", type=int, default=10, help="Max pages to scrape")
    parser.add_argument("--delay", type=float, default=5.0, help="Delay between requests")
    parser.add_argument("--details", action="store_true", help="Also fetch full release details")
    args = parser.parse_args()

    main(max_pages=args.pages, delay=args.delay, fetch_details=args.details)
