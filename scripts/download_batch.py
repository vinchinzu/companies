#!/usr/bin/env python3
"""Batch download SEC complaint PDFs with very conservative rate limiting.

This script is designed to run overnight or over several hours with very
long delays between requests to avoid triggering SEC rate limits.
"""

import os
import time
import random
from pathlib import Path
from datetime import datetime

import requests

# More complete list of complaint numbers to try
# Based on SEC numbering patterns, 2025 starts around 26200+

COMPLAINTS_2025 = [
    # Known working (already have these)
    # 26219, 26229, 26300, 26315, 26352, 26358, 26366, 26371,
    # 26383, 26392, 26393, 26420, 26423, 26446,

    # Additional 2025 numbers to try (fill in gaps and extend range)
    26201, 26202, 26203, 26204, 26205, 26206, 26207, 26208, 26209, 26210,
    26211, 26212, 26213, 26214, 26215, 26216, 26217, 26218,
    26220, 26221, 26222, 26223, 26224, 26225, 26226, 26227, 26228,
    26230, 26231, 26232, 26233, 26234, 26235, 26240, 26245, 26250,
    26255, 26260, 26265, 26270, 26275, 26280, 26285, 26290, 26295,
    26301, 26302, 26303, 26304, 26305, 26310, 26311, 26312, 26313, 26314,
    26316, 26317, 26318, 26319, 26320, 26325, 26330, 26335, 26340, 26345,
    26350, 26351, 26353, 26354, 26355, 26356, 26357,
    26359, 26360, 26361, 26362, 26363, 26364, 26365,
    26367, 26368, 26369, 26370, 26372, 26373, 26374, 26375,
    26376, 26377, 26378, 26379, 26380, 26381, 26382,
    26384, 26385, 26386, 26387, 26388, 26389, 26390, 26391,
    26394, 26395, 26396, 26397, 26398, 26399, 26400,
    26401, 26402, 26403, 26404, 26405, 26406, 26407, 26408, 26409, 26410,
    26411, 26412, 26413, 26414, 26415, 26416, 26417, 26418, 26419,
    26421, 26422, 26424, 26425, 26426, 26427, 26428, 26429, 26430,
    26431, 26432, 26433, 26434, 26435, 26440, 26441, 26442, 26443, 26444, 26445,
    26447, 26448, 26449, 26450, 26455, 26460, 26465, 26470, 26475, 26480,
    26485, 26490, 26495, 26500,
]

# For 2024, SEC complaints are in the same files structure
# They may use different numbering - let's try broader range
COMPLAINTS_2024 = [
    # Based on SEC complaint numbering going back from 26200
    26100, 26101, 26102, 26103, 26104, 26105, 26110, 26115, 26120, 26125,
    26130, 26135, 26140, 26145, 26150, 26155, 26160, 26165, 26170, 26175,
    26180, 26185, 26190, 26195, 26199,
    # Earlier 2024
    26000, 26005, 26010, 26015, 26020, 26025, 26030, 26035, 26040, 26045,
    26050, 26055, 26060, 26065, 26070, 26075, 26080, 26085, 26090, 26095,
    # Even earlier
    25900, 25905, 25910, 25915, 25920, 25925, 25930, 25935, 25940, 25945,
    25950, 25955, 25960, 25965, 25970, 25975, 25980, 25985, 25990, 25995,
    25800, 25810, 25820, 25830, 25840, 25850, 25860, 25870, 25880, 25890,
]

HEADERS_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
]


def download_pdf(year: int, comp_num: int, output_dir: Path) -> tuple[bool, str]:
    """Download a single PDF."""
    url = f"https://www.sec.gov/files/litigation/complaints/{year}/comp{comp_num}.pdf"
    filepath = output_dir / f"comp{comp_num}.pdf"

    # Skip if already exists and valid
    if filepath.exists() and filepath.stat().st_size > 5000:
        with open(filepath, "rb") as f:
            if f.read(4) == b"%PDF":
                return True, "have"

    headers = random.choice(HEADERS_POOL)

    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=60)

        if response.status_code == 403:
            if b"Request Rate Threshold" in response.content:
                return False, "RATE_LIMITED"
            return False, "403"

        if response.status_code == 404:
            return False, "404"

        response.raise_for_status()

        if response.content[:4] != b"%PDF":
            return False, "not_pdf"

        with open(filepath, "wb") as f:
            f.write(response.content)

        return True, f"{len(response.content):,}b"

    except requests.RequestException as e:
        return False, f"err:{str(e)[:20]}"


def main(year: int = 2025, max_downloads: int = 30, min_delay: int = 30, max_delay: int = 60):
    """Download PDFs with very conservative rate limiting."""
    output_dir = Path(f"data/pdfs/{year}")
    output_dir.mkdir(parents=True, exist_ok=True)

    complaints = COMPLAINTS_2025 if year == 2025 else COMPLAINTS_2024

    print("=" * 60)
    print(f"SEC Batch Downloader - {year}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"Complaints to try: {len(complaints)}")
    print(f"Max downloads: {max_downloads}")
    print(f"Delay: {min_delay}-{max_delay}s between requests")
    print("=" * 60)

    downloaded = []
    skipped = []
    not_found = []
    errors = []

    for i, comp_num in enumerate(complaints):
        if len(downloaded) >= max_downloads:
            print(f"\nReached max downloads ({max_downloads})")
            break

        # Check if already have
        filepath = output_dir / f"comp{comp_num}.pdf"
        if filepath.exists() and filepath.stat().st_size > 5000:
            with open(filepath, "rb") as f:
                if f.read(4) == b"%PDF":
                    skipped.append(comp_num)
                    continue

        print(f"[{len(downloaded)+1}/{max_downloads}] comp{comp_num}...", end=" ", flush=True)

        success, msg = download_pdf(year, comp_num, output_dir)

        if success and msg != "have":
            downloaded.append(comp_num)
            print(f"OK ({msg})")
        elif msg == "404":
            not_found.append(comp_num)
            print("not found")
        elif msg == "RATE_LIMITED":
            print("RATE LIMITED - stopping")
            errors.append(comp_num)
            break
        else:
            errors.append(comp_num)
            print(msg)

        # Conservative delay
        delay = random.uniform(min_delay, max_delay)
        print(f"    Waiting {delay:.0f}s...")
        time.sleep(delay)

    # Summary
    print("\n" + "=" * 60)
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"Downloaded: {len(downloaded)}")
    print(f"Already had: {len(skipped)}")
    print(f"Not found: {len(not_found)}")
    print(f"Errors: {len(errors)}")

    if downloaded:
        print(f"\nNew files: {downloaded}")

    # Count total valid PDFs
    valid = sum(1 for p in output_dir.glob("*.pdf")
                if p.stat().st_size > 5000 and open(p, "rb").read(4) == b"%PDF")
    print(f"\nTotal valid PDFs in {output_dir}: {valid}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--max", type=int, default=20)
    parser.add_argument("--min-delay", type=int, default=30)
    parser.add_argument("--max-delay", type=int, default=60)
    args = parser.parse_args()

    main(year=args.year, max_downloads=args.max,
         min_delay=args.min_delay, max_delay=args.max_delay)
