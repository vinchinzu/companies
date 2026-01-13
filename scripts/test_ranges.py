#!/usr/bin/env python3
"""Quick probe for valid SEC complaint number ranges."""
import requests
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
}

def check_exists(year, num):
    url = f"https://www.sec.gov/files/litigation/complaints/{year}/comp{num}.pdf"
    try:
        resp = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
        return resp.status_code == 200
    except:
        return False

# Test different ranges for 2024
print("Testing 2024 ranges...")
ranges_to_test = [
    (25000, 25050),  # Early range
    (25200, 25250),  # Mid range  
    (25400, 25450),  # Another range
    (25600, 25650),  # Later range
    (25800, 25850),  # Even later
    (26000, 26050),  # Late 2024
]

found = []
for start, end in ranges_to_test:
    for num in [start, start+10, start+25, end]:
        exists = check_exists(2024, num)
        status = "FOUND" if exists else "not found"
        print(f"  2024/comp{num}: {status}")
        if exists:
            found.append(num)
        time.sleep(2)  # Be polite

print(f"\nFound valid 2024 numbers: {found}")
