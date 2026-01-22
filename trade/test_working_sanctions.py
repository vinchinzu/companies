#!/usr/bin/env python3
"""
Working sanctions test using OpenSanctions bulk data.
Tests with companies from your fraudulent_companies.csv dataset.
"""

import requests
import sys

# Known sanctioned companies from your dataset
SANCTIONED_COMPANIES = [
    "Central Bank of Iran",
    "Korea Myongdok Shipping",
    "Joint Stock Company Polyot",
    "TPK Vostok Resurs",
    "Atropars Company"
]

# Clean companies (should NOT match)
CLEAN_COMPANIES = [
    "Apple Inc",
    "Microsoft Corporation",
    "Tesla Inc"
]


def download_sanctions_list():
    """Download OFAC SDN names list from OpenSanctions."""
    print("Downloading OFAC Specially Designated Nationals list...")
    print("Source: https://data.opensanctions.org\n")

    url = "https://data.opensanctions.org/datasets/latest/us_ofac_sdn/names.txt"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        names = set()
        for line in response.text.split('\n'):
            name = line.strip()
            if name:
                names.add(name.lower())

        print(f"✓ Downloaded {len(names):,} sanctioned entity names\n")
        return names

    except Exception as e:
        print(f"✗ Error downloading data: {e}")
        return None


def check_sanctions(company_name, sanctions_list):
    """Check if company matches any sanctioned entity."""

    company_lower = company_name.lower()

    # Exact match
    if company_lower in sanctions_list:
        return {
            'match': True,
            'type': 'exact',
            'confidence': 1.0,
            'matched': company_name
        }

    # Partial match (substring)
    for sanctioned_name in sanctions_list:
        if company_lower in sanctioned_name or sanctioned_name in company_lower:
            return {
                'match': True,
                'type': 'partial',
                'confidence': 0.8,
                'matched': sanctioned_name
            }

    return {
        'match': False,
        'type': None,
        'confidence': 0.0,
        'matched': None
    }


def run_tests():
    """Run sanctions checking tests."""

    print("=" * 70)
    print("SANCTIONS CHECKING TEST - OpenSanctions OFAC Data")
    print("=" * 70)
    print()

    # Download data
    sanctions_list = download_sanctions_list()

    if not sanctions_list:
        print("Failed to download sanctions data")
        return 1

    # Test sanctioned companies
    print("=" * 70)
    print("TEST 1: Known Sanctioned Entities (Should Match)")
    print("=" * 70)
    print()

    sanctioned_results = []

    for company in SANCTIONED_COMPANIES:
        result = check_sanctions(company, sanctions_list)

        if result['match']:
            print(f"🔴 {company}")
            print(f"   Match: {result['type']}")
            print(f"   Confidence: {result['confidence']:.0%}")
            if result['matched'] != company.lower():
                print(f"   Matched name: {result['matched']}")
            print()
            sanctioned_results.append('PASS')
        else:
            print(f"⚠️  {company}")
            print(f"   Expected sanctions hit but found none!")
            print(f"   (May be in different OFAC list or name variant)")
            print()
            sanctioned_results.append('FAIL')

    # Test clean companies
    print("=" * 70)
    print("TEST 2: Clean Companies (Should NOT Match)")
    print("=" * 70)
    print()

    clean_results = []

    for company in CLEAN_COMPANIES:
        result = check_sanctions(company, sanctions_list)

        if not result['match']:
            print(f"🟢 {company}")
            print(f"   No sanctions found (as expected)")
            print()
            clean_results.append('PASS')
        else:
            print(f"⚠️  {company}")
            print(f"   Unexpected sanctions hit!")
            print(f"   Match: {result['type']}")
            print(f"   Matched: {result['matched']}")
            print()
            clean_results.append('FAIL')

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print()

    sanctioned_pass = sanctioned_results.count('PASS')
    clean_pass = clean_results.count('PASS')
    total_pass = sanctioned_pass + clean_pass
    total_tests = len(sanctioned_results) + len(clean_results)

    print(f"Sanctioned entities detected: {sanctioned_pass}/{len(sanctioned_results)}")
    print(f"Clean companies verified: {clean_pass}/{len(clean_results)}")
    print(f"\nTotal: {total_pass}/{total_tests} tests passed")
    print()

    if total_pass == total_tests:
        print("✓ All tests passed! Sanctions checking is working correctly.")
        print()
        return 0
    else:
        print("⚠ Some tests did not pass as expected.")
        print()
        print("Note: Partial failures may occur if:")
        print("  - Entity is in a different OFAC list (not SDN)")
        print("  - Name spelling differs from OFAC records")
        print("  - Entity was added/removed recently")
        print()
        return 1


def demo_usage():
    """Show how to use in the company verifier tool."""

    print("=" * 70)
    print("INTEGRATION EXAMPLE")
    print("=" * 70)
    print("""
To integrate this into your company_verifier.py:

# 1. Download sanctions list once (cache it)
sanctions_list = download_sanctions_list()

# 2. Check companies
def verify_company(company_name):
    result = check_sanctions(company_name, sanctions_list)

    if result['match']:
        print(f"⚠️  SANCTIONS HIT: {company_name}")
        print(f"   Confidence: {result['confidence']:.0%}")
        return {
            'risk_level': 'HIGH',
            'reason': 'Found on OFAC sanctions list'
        }
    else:
        return {
            'risk_level': 'LOW',
            'reason': 'No sanctions matches found'
        }

# 3. Or use the full implementation from your other tool:
# cp ../company/company-research-tool/scrapers/opensanctions.py ./modules/
    """)


if __name__ == '__main__':
    exit_code = run_tests()
    demo_usage()
    sys.exit(exit_code)
