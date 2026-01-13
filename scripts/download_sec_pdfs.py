#!/usr/bin/env python3
"""Script to download SEC complaint PDFs from 2025."""

import os
import sys
import time
import random
from pathlib import Path

import requests

# Known complaint numbers from 2025 (from web searches)
# Starting from ~26200 (late 2024/early 2025) through ~26500
COMPLAINT_RANGE_2025 = list(range(26200, 26500))

BASE_URL = "https://www.sec.gov/files/litigation/complaints/2025/comp{}.pdf"

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    },
]


def download_pdf(complaint_num: int, output_dir: Path, delay: float = 3.0) -> tuple[bool, str]:
    """Download a single SEC complaint PDF.

    Returns (success, message).
    """
    url = BASE_URL.format(complaint_num)
    filename = f"comp{complaint_num}.pdf"
    filepath = output_dir / filename

    # Skip if already downloaded and valid
    if filepath.exists() and filepath.stat().st_size > 5000:
        # Verify it's a PDF
        with open(filepath, "rb") as f:
            if f.read(4) == b"%PDF":
                return True, "already exists"

    headers = random.choice(HEADERS_LIST)

    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=30, allow_redirects=True)

        # Check for rate limiting
        if response.status_code == 403:
            if b"Request Rate Threshold" in response.content:
                return False, "rate limited"
            return False, "forbidden"

        if response.status_code == 404:
            return False, "not found"

        response.raise_for_status()

        # Verify it's a PDF
        if not response.content[:4] == b"%PDF":
            return False, "not a PDF"

        # Save the PDF
        with open(filepath, "wb") as f:
            f.write(response.content)

        time.sleep(delay + random.uniform(0, 2))  # Add jitter
        return True, f"downloaded ({len(response.content)} bytes)"

    except requests.RequestException as e:
        return False, str(e)[:50]


def main(max_downloads: int = 25, delay: float = 4.0):
    """Download SEC complaint PDFs."""
    output_dir = Path("data/pdfs/2025")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track results
    log_file = output_dir / "download_log.txt"

    print("=" * 60)
    print("SEC Complaint PDF Downloader - 2025")
    print("=" * 60)
    print(f"Output directory: {output_dir}")
    print(f"Max downloads this run: {max_downloads}")
    print(f"Delay between requests: {delay}s + jitter")
    print("=" * 60)

    downloaded = 0
    already_had = 0
    not_found = 0
    rate_limited = False

    with open(log_file, "a", encoding='utf-8') as log:
        log.write(f"\n=== Download run at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")

        for comp_num in COMPLAINT_RANGE_2025:
            if downloaded >= max_downloads:
                print(f"\nReached max downloads ({max_downloads})")
                break

            if rate_limited:
                print("\nRate limited - stopping to avoid ban")
                break

            filepath = output_dir / f"comp{comp_num}.pdf"

            # Check if we already have a valid PDF
            if filepath.exists() and filepath.stat().st_size > 5000:
                with open(filepath, "rb") as f:
                    if f.read(4) == b"%PDF":
                        already_had += 1
                        continue

            print(f"[{downloaded+1}/{max_downloads}] comp{comp_num}...", end=" ", flush=True)

            success, message = download_pdf(comp_num, output_dir, delay)

            if success:
                if "already" in message:
                    already_had += 1
                    print("(already had)")
                else:
                    downloaded += 1
                    print(f"OK - {message}")
                    log.write(f"comp{comp_num}.pdf - {message}\n")
            else:
                if "rate limited" in message:
                    rate_limited = True
                    print("RATE LIMITED")
                    log.write(f"comp{comp_num} - RATE LIMITED\n")
                elif "not found" in message:
                    not_found += 1
                    print("not found")
                else:
                    print(f"failed: {message}")
                    log.write(f"comp{comp_num} - failed: {message}\n")

        log.write(f"Downloaded: {downloaded}, Already had: {already_had}, Not found: {not_found}\n")

    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)
    print(f"New downloads: {downloaded}")
    print(f"Already had: {already_had}")
    print(f"Not found: {not_found}")
    if rate_limited:
        print("Status: RATE LIMITED - run again later")

    # List all valid PDFs
    valid_pdfs = []
    for pdf in output_dir.glob("*.pdf"):
        with open(pdf, "rb") as f:
            if f.read(4) == b"%PDF":
                valid_pdfs.append(pdf.name)

    print(f"\nTotal valid PDFs in {output_dir}: {len(valid_pdfs)}")
    if valid_pdfs:
        print("Files:")
        for pdf in sorted(valid_pdfs)[:20]:
            print(f"  - {pdf}")
        if len(valid_pdfs) > 20:
            print(f"  ... and {len(valid_pdfs) - 20} more")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download SEC complaint PDFs")
    parser.add_argument("--max", type=int, default=25, help="Max PDFs to download")
    parser.add_argument("--delay", type=float, default=4.0, help="Delay between requests")
    args = parser.parse_args()

    main(max_downloads=args.max, delay=args.delay)
