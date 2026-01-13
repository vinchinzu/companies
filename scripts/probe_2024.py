#!/usr/bin/env python3
"""Probe different URL patterns for 2024 SEC complaints."""
import requests
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
}

# Try different URL patterns SEC might use
patterns = [
    # Standard pattern
    "https://www.sec.gov/files/litigation/complaints/2024/comp{}.pdf",
    # Alternative patterns
    "https://www.sec.gov/litigation/complaints/2024/comp{}.pdf",
    "https://www.sec.gov/files/litigation/complaints/comp{}.pdf",
    # Named complaints (some SEC complaints use names)
    "https://www.sec.gov/files/litigation/complaints/2024/comp-{}.pdf",
]

# Known case names that might have PDFs
known_cases = [
    "terraform", "hyperfund", "novatech", "ftx", "blockfi",
    "coinbase", "binance", "kraken", "gemini", "ripple"
]

print("Testing URL patterns...")
for pattern in patterns[:2]:  # Just test first two patterns
    test_url = pattern.format("25000")
    try:
        resp = requests.head(test_url, headers=HEADERS, timeout=10)
        print(f"  Pattern: {pattern[:60]}... -> {resp.status_code}")
    except Exception as e:
        print(f"  Pattern: {pattern[:60]}... -> Error: {e}")
    time.sleep(1)

print("\nTrying named complaint URLs...")
for case in known_cases[:5]:
    url = f"https://www.sec.gov/files/litigation/complaints/2024/comp-{case}.pdf"
    try:
        resp = requests.head(url, headers=HEADERS, timeout=10)
        status = "FOUND!" if resp.status_code == 200 else resp.status_code
        print(f"  comp-{case}: {status}")
    except Exception as e:
        print(f"  comp-{case}: Error")
    time.sleep(1)

# Try lower ranges
print("\nTesting lower number ranges (maybe 2024 starts earlier)...")
for num in [24000, 24500, 24800, 24900]:
    url = f"https://www.sec.gov/files/litigation/complaints/2024/comp{num}.pdf"
    try:
        resp = requests.head(url, headers=HEADERS, timeout=10)
        status = "FOUND!" if resp.status_code == 200 else "not found"
        print(f"  2024/comp{num}: {status}")
    except Exception as e:
        print(f"  2024/comp{num}: Error")
    time.sleep(1)
