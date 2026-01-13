#!/usr/bin/env python3
"""Download only the known-good SEC complaint PDFs from 2025."""

import os
import time
import random
from pathlib import Path

import requests

# These are the complaint numbers confirmed to exist from web searches
KNOWN_GOOD_2025 = [
    26219,  # Elon Musk / Twitter
    26229,  # Nova Labs
    26300,  # StHealth Capital
    26315,  # Anchor State
    26352,  # CaaStle / Hunsicker
    26358,  # First Liberty / Frost
    26366,  # Unknown
    26371,  # Ryan Cole spoofing
    26383,  # NJ case
    26392,  # Unknown
    26393,  # Vukota Capital
    26416,  # Bluesky Eagle
    26420,  # Unknown
    26423,  # SolarWinds
    26446,  # Ammo Inc
]

BASE_URL = "https://www.sec.gov/files/litigation/complaints/2025/comp{}.pdf"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
}


def download_with_retry(comp_num: int, output_dir: Path, max_retries: int = 3) -> bool:
    """Download PDF with retries and exponential backoff."""
    url = BASE_URL.format(comp_num)
    filepath = output_dir / f"comp{comp_num}.pdf"

    for attempt in range(max_retries):
        delay = (attempt + 1) * 10 + random.uniform(5, 15)  # 15-25s, 25-35s, 35-45s

        if attempt > 0:
            print(f"    Retry {attempt + 1}/{max_retries} after {delay:.0f}s...")
            time.sleep(delay)

        try:
            session = requests.Session()
            response = session.get(url, headers=HEADERS, timeout=60)

            if response.status_code == 403:
                if b"Request Rate Threshold" in response.content:
                    print(f"    Rate limited, waiting {delay * 2:.0f}s...")
                    time.sleep(delay * 2)
                    continue
                return False

            if response.status_code == 404:
                return False

            response.raise_for_status()

            if response.content[:4] != b"%PDF":
                return False

            with open(filepath, "wb") as f:
                f.write(response.content)

            return True

        except requests.RequestException as e:
            print(f"    Error: {str(e)[:40]}")
            continue

    return False


def main():
    """Download known SEC PDFs."""
    output_dir = Path("data/pdfs/2025")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("SEC Known PDF Downloader - 2025")
    print("=" * 60)
    print(f"Attempting {len(KNOWN_GOOD_2025)} known complaint PDFs")
    print("Using long delays to avoid rate limiting")
    print("=" * 60)

    downloaded = []
    failed = []

    for i, comp_num in enumerate(KNOWN_GOOD_2025):
        filepath = output_dir / f"comp{comp_num}.pdf"

        # Skip if valid PDF exists
        if filepath.exists() and filepath.stat().st_size > 5000:
            with open(filepath, "rb") as f:
                if f.read(4) == b"%PDF":
                    print(f"[{i+1}/{len(KNOWN_GOOD_2025)}] comp{comp_num} - already have")
                    downloaded.append(comp_num)
                    continue

        print(f"[{i+1}/{len(KNOWN_GOOD_2025)}] comp{comp_num}...", end=" ", flush=True)

        if download_with_retry(comp_num, output_dir):
            size = filepath.stat().st_size
            print(f"OK ({size:,} bytes)")
            downloaded.append(comp_num)
        else:
            print("FAILED")
            failed.append(comp_num)

        # Long delay between files
        if i < len(KNOWN_GOOD_2025) - 1:
            wait = random.uniform(8, 15)
            print(f"    Waiting {wait:.0f}s before next...")
            time.sleep(wait)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Downloaded: {len(downloaded)}")
    print(f"Failed: {len(failed)}")

    if downloaded:
        print(f"\nSuccess: {downloaded}")
    if failed:
        print(f"Failed: {failed}")


if __name__ == "__main__":
    main()
