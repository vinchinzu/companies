#!/usr/bin/env python3
"""
Test the fixed ITA API implementation.
"""

import sys

# Test cases
TEST_CASES = [
    {
        "name": "Central Bank of Iran",
        "expected": "HIGH_RISK",
        "expected_hits": "> 0",
        "description": "Known OFAC sanctioned entity"
    },
    {
        "name": "Korea Myongdok Shipping",
        "expected": "HIGH_RISK",
        "expected_hits": "> 0",
        "description": "North Korean sanctioned entity"
    },
    {
        "name": "Apple Inc.",
        "expected": "LOW_RISK",
        "expected_hits": "0",
        "description": "Legitimate US tech company"
    },
    {
        "name": "Microsoft Corporation",
        "expected": "LOW_RISK",
        "expected_hits": "0",
        "description": "Legitimate US tech company"
    },
    {
        "name": "Fake Shell Company LLC",
        "expected": "MEDIUM_RISK",
        "expected_hits": "0",
        "description": "Non-existent company"
    }
]


def run_tests():
    """Run all test cases."""
    print("=" * 80)
    print("FIXED ITA API - COMPREHENSIVE TEST")
    print("=" * 80)
    print()

    from modules.sanctions_checker import SanctionsChecker

    checker = SanctionsChecker()

    if not checker.ita_client:
        print("❌ ITA API not configured")
        return 1

    print("✓ ITA API configured")
    print()

    results = []

    for i, test in enumerate(TEST_CASES, 1):
        print(f"Test {i}/{len(TEST_CASES)}: {test['name']}")
        print(f"  Description: {test['description']}")
        print(f"  Expected: {test['expected']} (sanctions hits: {test['expected_hits']})")

        # Check sanctions
        result = checker.check(test['name'])
        hits = result.get('sanctions_hits', 0)

        print(f"  Actual: {hits} sanctions hit(s)")

        # Determine pass/fail
        if test['expected_hits'] == "0":
            passed = (hits == 0)
        elif test['expected_hits'] == "> 0":
            passed = (hits > 0)
        else:
            passed = False

        if passed:
            print(f"  ✅ PASS")
        else:
            print(f"  ❌ FAIL")

        print()

        results.append({
            'test': test['name'],
            'passed': passed,
            'hits': hits
        })

    checker.close()

    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for r in results if r['passed'])
    total = len(results)

    for result in results:
        status = "✅ PASS" if result['passed'] else "❌ FAIL"
        print(f"{status:10} | {result['test']:30} | Hits: {result['hits']}")

    print()
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print()

    if passed == total:
        print("✅ All tests passed! ITA API is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. See details above.")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
