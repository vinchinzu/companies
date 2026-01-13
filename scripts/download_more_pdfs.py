#!/usr/bin/env python3
"""Download SEC complaint PDFs from 2024 and 2025 with smart probing."""

import os
import time
import random
from pathlib import Path
from datetime import datetime

import requests

# URL patterns for different years
BASE_URLS = {
    2024: "https://www.sec.gov/files/litigation/complaints/2024/comp{}.pdf",
    2025: "https://www.sec.gov/files/litigation/complaints/2025/comp{}.pdf",
}

# Estimated complaint number ranges per year
# SEC complaint numbers are sequential across years
RANGES = {
    2024: list(range(25800, 26220)),  # Early 2024 through late 2024
    2025: list(range(26200, 26500)),  # 2025 range
}

# Additional specific numbers to try based on typical patterns
# SEC sometimes has gaps in numbering
SPECIFIC_NUMBERS = {
    2024: [
        # Major 2024 cases - estimated numbers
        25850, 25875, 25900, 25925, 25950, 25975,
        26000, 26025, 26050, 26075, 26100, 26125, 26150, 26175, 26200,
        # Fill in gaps
        25801, 25810, 25820, 25830, 25840, 25860, 25870, 25880, 25890,
        25910, 25920, 25930, 25940, 25960, 25970, 25980, 25990,
        26010, 26020, 26030, 26040, 26060, 26070, 26080, 26090,
        26110, 26120, 26130, 26140, 26160, 26170, 26180, 26190,
    ],
    2025: [
        # Additional 2025 numbers not yet downloaded
        26220, 26225, 26230, 26235, 26240, 26245, 26250,
        26255, 26260, 26265, 26270, 26275, 26280, 26285, 26290, 26295,
        26305, 26310, 26320, 26325, 26330, 26335, 26340, 26345, 26350,
        26355, 26360, 26365, 26370, 26375, 26380, 26385, 26390, 26395,
        26400, 26405, 26410, 26415, 26425, 26430, 26435, 26440, 26445,
        26450, 26455, 26460, 26465, 26470, 26475, 26480, 26485, 26490,
    ],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
}


def download_pdf(year: int, comp_num: int, output_dir: Path, max_retries: int = 2) -> tuple[bool, str]:
    """Download a single PDF with retries.

    Returns (success, message).
    """
    url = BASE_URLS[year].format(comp_num)
    filepath = output_dir / f"comp{comp_num}.pdf"

    # Skip if already exists and valid
    if filepath.exists() and filepath.stat().st_size > 5000:
        with open(filepath, "rb") as f:
            if f.read(4) == b"%PDF":
                return True, "already have"

    for attempt in range(max_retries):
        if attempt > 0:
            delay = (attempt + 1) * 15 + random.uniform(5, 15)
            time.sleep(delay)

        try:
            session = requests.Session()
            response = session.get(url, headers=HEADERS, timeout=60)

            if response.status_code == 403:
                if b"Request Rate Threshold" in response.content:
                    return False, "RATE LIMITED"
                return False, "forbidden"

            if response.status_code == 404:
                return False, "not found"

            response.raise_for_status()

            # Verify it's a PDF
            if response.content[:4] != b"%PDF":
                return False, "not a PDF"

            with open(filepath, "wb") as f:
                f.write(response.content)

            return True, f"OK ({len(response.content):,} bytes)"

        except requests.RequestException as e:
            if attempt == max_retries - 1:
                return False, f"error: {str(e)[:30]}"

    return False, "max retries"


def main(year: int = 2024, max_downloads: int = 20, start_from: int = None):
    """Download PDFs for specified year."""
    output_dir = Path(f"data/pdfs/{year}")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"SEC PDF Downloader - {year}")
    print("=" * 60)
    print(f"Output: {output_dir}")
    print(f"Max downloads: {max_downloads}")
    print(f"Using 10-20s delays to avoid rate limiting")
    print("=" * 60)

    # Get numbers to try
    numbers = sorted(set(SPECIFIC_NUMBERS.get(year, [])))
    if start_from:
        numbers = [n for n in numbers if n >= start_from]

    downloaded = []
    failed = []
    not_found = []
    rate_limited = False

    for i, comp_num in enumerate(numbers):
        if len(downloaded) >= max_downloads:
            print(f"\nReached max downloads ({max_downloads})")
            break

        if rate_limited:
            print("\nRate limited - stopping")
            break

        # Check if we already have it
        filepath = output_dir / f"comp{comp_num}.pdf"
        if filepath.exists() and filepath.stat().st_size > 5000:
            with open(filepath, "rb") as f:
                if f.read(4) == b"%PDF":
                    continue  # Skip silently

        print(f"[{len(downloaded)+1}/{max_downloads}] {year}/comp{comp_num}...", end=" ", flush=True)

        success, message = download_pdf(year, comp_num, output_dir)

        if success:
            if "already" not in message:
                downloaded.append(comp_num)
                print(message)
            else:
                print("(skip)")
        else:
            if "RATE" in message:
                rate_limited = True
                print(message)
                failed.append(comp_num)
            elif "not found" in message:
                not_found.append(comp_num)
                print("not found")
            else:
                print(message)
                failed.append(comp_num)

        # Longer delay between requests
        if not rate_limited and len(downloaded) < max_downloads:
            wait = random.uniform(10, 20)
            print(f"    Waiting {wait:.0f}s...")
            time.sleep(wait)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Downloaded: {len(downloaded)}")
    print(f"Not found: {len(not_found)}")
    print(f"Failed: {len(failed)}")

    if downloaded:
        print(f"\nNew files: {downloaded}")

    # List all valid PDFs
    valid_pdfs = []
    for pdf in output_dir.glob("*.pdf"):
        with open(pdf, "rb") as f:
            if f.read(4) == b"%PDF":
                valid_pdfs.append(pdf.name)

    print(f"\nTotal valid PDFs in {output_dir}: {len(valid_pdfs)}")

    return downloaded, not_found, failed


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download SEC complaint PDFs")
    parser.add_argument("--year", type=int, default=2024, choices=[2024, 2025],
                       help="Year to download")
    parser.add_argument("--max", type=int, default=15, help="Max PDFs to download")
    parser.add_argument("--start", type=int, help="Start from this complaint number")
    args = parser.parse_args()

    main(year=args.year, max_downloads=args.max, start_from=args.start)
