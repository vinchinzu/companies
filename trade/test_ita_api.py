#!/usr/bin/env python3
"""
Test script for ITA Consolidated Screening List API.
Tests with known sanctioned entities from the fraudulent companies dataset.
"""

import requests
import sys
from config import Config

# Test companies from the fraudulent companies dataset
TEST_COMPANIES = [
    {
        "name": "Joint Stock Company Polyot Research and Production Company",
        "expected": "sanctioned",
        "country": "ru"
    },
    {
        "name": "Central Bank of Iran",
        "expected": "sanctioned",
        "country": "ir"
    },
    {
        "name": "Korea Myongdok Shipping",
        "expected": "sanctioned",
        "country": "kp"
    },
    {
        "name": "Apple Inc",
        "expected": "clean",
        "country": "us"
    },
    {
        "name": "Microsoft Corporation",
        "expected": "clean",
        "country": "us"
    }
]


def test_ita_api(company_name, fuzzy=True):
    """
    Test ITA Consolidated Screening List API.

    Args:
        company_name: Company name to search
        fuzzy: Use fuzzy name matching

    Returns:
        API response or None on error
    """
    if not Config.ITA_SUBSCRIPTION_KEY:
        print("ERROR: ITA API key not configured")
        print("Make sure PRIMARY_KEY is set in .env file")
        return None

    base_url = Config.ITA_BASE_URL
    headers = {
        'subscription-key': Config.ITA_SUBSCRIPTION_KEY
    }

    params = {
        'name': company_name,
        'fuzzy_name': 'true' if fuzzy else 'false',
        'size': 10
    }

    try:
        print(f"\n{'=' * 70}")
        print(f"Testing: {company_name}")
        print('=' * 70)

        response = requests.get(
            f"{base_url}/v1/consolidated_screening_list/search",
            headers=headers,
            params=params,
            timeout=30
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            results = data.get('results', [])

            print(f"Total Matches: {total}")

            if total > 0:
                print("\nMatches Found:")
                for i, hit in enumerate(results[:5], 1):
                    print(f"\n  {i}. {hit.get('name', 'N/A')}")
                    print(f"     Source: {hit.get('source', 'N/A')}")
                    print(f"     Type: {hit.get('type', 'N/A')}")

                    programs = hit.get('programs', [])
                    if programs:
                        print(f"     Programs: {', '.join(programs)}")

                    addresses = hit.get('addresses', [])
                    if addresses and len(addresses) > 0:
                        addr = addresses[0]
                        country = addr.get('country', 'N/A')
                        print(f"     Country: {country}")

                    remarks = hit.get('remarks', '')
                    if remarks:
                        print(f"     Remarks: {remarks[:100]}...")

                return data
            else:
                print("✓ No sanctions matches found (clean)")
                return data

        elif response.status_code == 401:
            print("ERROR: Authentication failed")
            print("Check that PRIMARY_KEY in .env is correct")
            return None

        elif response.status_code == 429:
            print("ERROR: Rate limit exceeded")
            return None

        else:
            print(f"ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request failed - {e}")
        return None


def run_all_tests():
    """Run tests on all test companies."""
    print("\n" + "=" * 70)
    print("ITA CONSOLIDATED SCREENING LIST API TEST")
    print("=" * 70)

    if not Config.ITA_SUBSCRIPTION_KEY:
        print("\nERROR: PRIMARY_KEY not configured in .env file")
        print("\nCurrent .env configuration:")
        print(f"  PRIMARY_KEY: {'SET' if Config.ITA_SUBSCRIPTION_KEY else 'NOT SET'}")
        sys.exit(1)

    print(f"\nAPI Key configured: {Config.ITA_SUBSCRIPTION_KEY[:10]}...{Config.ITA_SUBSCRIPTION_KEY[-4:]}")
    print(f"API Base URL: {Config.ITA_BASE_URL}")

    results = []

    for test in TEST_COMPANIES:
        result = test_ita_api(test['name'])

        if result is not None:
            total = result.get('total', 0)
            expected = test['expected']

            # Validate result
            if expected == 'sanctioned' and total > 0:
                status = "✓ PASS"
            elif expected == 'clean' and total == 0:
                status = "✓ PASS"
            elif expected == 'sanctioned' and total == 0:
                status = "⚠ FAIL (Expected sanctions hit, got none)"
            elif expected == 'clean' and total > 0:
                status = "⚠ FAIL (Expected clean, got sanctions hit)"
            else:
                status = "? UNCLEAR"

            results.append({
                'name': test['name'],
                'expected': expected,
                'hits': total,
                'status': status
            })

            print(f"\nResult: {status}")
        else:
            results.append({
                'name': test['name'],
                'expected': test['expected'],
                'hits': 'ERROR',
                'status': "✗ ERROR"
            })

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for result in results:
        print(f"{result['status']:20} | {result['name'][:40]:40} | Hits: {result['hits']}")

    passed = sum(1 for r in results if 'PASS' in r['status'])
    total_tests = len(results)

    print("\n" + "=" * 70)
    print(f"Results: {passed}/{total_tests} tests passed")
    print("=" * 70)

    if passed == total_tests:
        print("\n✓ All tests passed! ITA API is working correctly.")
        return 0
    else:
        print("\n⚠ Some tests failed. Check API configuration or network.")
        return 1


def test_single_company(company_name):
    """Test a single company name."""
    print("\n" + "=" * 70)
    print("ITA API SINGLE COMPANY TEST")
    print("=" * 70)

    if not Config.ITA_SUBSCRIPTION_KEY:
        print("\nERROR: PRIMARY_KEY not configured in .env file")
        sys.exit(1)

    result = test_ita_api(company_name)

    if result:
        total = result.get('total', 0)
        if total > 0:
            print(f"\n🔴 WARNING: {total} sanctions hit(s) found for '{company_name}'")
            return 2
        else:
            print(f"\n🟢 CLEAR: No sanctions hits for '{company_name}'")
            return 0
    else:
        print("\n✗ Test failed due to API error")
        return 1


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Test ITA Consolidated Screening List API'
    )
    parser.add_argument(
        '--company',
        help='Test a specific company name'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all predefined tests'
    )

    args = parser.parse_args()

    if args.company:
        exit_code = test_single_company(args.company)
    elif args.all:
        exit_code = run_all_tests()
    else:
        # Default: run all tests
        exit_code = run_all_tests()

    sys.exit(exit_code)
