#!/usr/bin/env python3
"""
Company Verifier Tool - MVP
Investigates companies for shell company indicators using open-source data.

Usage:
    python company_verifier.py --name "Company Name" --country US
    python company_verifier.py --name "Company Name" --country GB --hs-code 85
"""

import argparse
import json
import sys
from typing import Dict, Any

from config import Config
from modules.registry_checker import RegistryChecker
from modules.sanctions_checker import SanctionsChecker
from modules.offshore_checker import OffshoreChecker
from modules.trade_checker import TradeChecker
from modules.risk_scorer import RiskScorer


def print_banner():
    """Print welcome banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║          Company Verification Tool - Shell Detection         ║
║                           MVP v1.0                           ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def verify_company(
    company_name: str,
    country: str = 'US',
    hs_code: str = None,
    output_json: bool = False
) -> Dict[str, Any]:
    """
    Run complete company verification.

    Args:
        company_name: Company name to verify
        country: Country code (US, GB, etc.)
        hs_code: Optional HS code for trade checking
        output_json: If True, return JSON only without printing

    Returns:
        Complete verification results
    """
    if not output_json:
        print_banner()
        print(f"Investigating: {company_name}")
        print(f"Jurisdiction: {country}")
        print(f"HS Code: {hs_code or 'Not specified'}")

    # Initialize modules
    registry_checker = RegistryChecker()
    sanctions_checker = SanctionsChecker()
    offshore_checker = OffshoreChecker()
    trade_checker = TradeChecker()
    risk_scorer = RiskScorer()

    results = {
        'company_name': company_name,
        'jurisdiction': country,
        'hs_code': hs_code
    }

    try:
        # 1. Registry Check
        if not output_json:
            print_section("1. REGISTRY VERIFICATION")
            print("Checking official company registries...")

        registry_result = registry_checker.check(company_name, country)
        results['registry'] = registry_result

        if not output_json:
            if registry_result.get('found'):
                print(f"✓ Company found: {registry_result.get('company_name', company_name)}")
                print(f"  Status: {registry_result.get('status', 'unknown')}")
                print(f"  Jurisdiction: {registry_result.get('jurisdiction')}")

                if country == 'GB':
                    print(f"  Company Number: {registry_result.get('company_number')}")
                    print(f"  Incorporation: {registry_result.get('incorporation_date', 'N/A')}")
                    print(f"  Officers: {registry_result.get('officers_count', 0)}")
                elif country == 'US':
                    print(f"  CIK: {registry_result.get('cik')}")
                    print(f"  SIC: {registry_result.get('sic')} - {registry_result.get('sic_description')}")
                    print(f"  Recent 10-K: {registry_result.get('recent_10k_date', 'None')}")

                if registry_result.get('red_flags'):
                    print(f"\n  ⚠ Red Flags:")
                    for flag in registry_result['red_flags']:
                        print(f"    - {flag}")
            else:
                print(f"✗ Company not found in {country} registry")

        # Extract officers for sanctions screening
        officers = []
        # Note: Would need to parse from detailed registry results in production

        # 2. Sanctions Check
        if not output_json:
            print_section("2. SANCTIONS SCREENING")
            print("Screening against sanctions lists and PEPs...")

        sanctions_result = sanctions_checker.check(company_name, officers)
        results['sanctions'] = sanctions_result

        if not output_json:
            if sanctions_result.get('sanctions_hits', 0) > 0:
                print(f"⚠ SANCTIONS HITS: {sanctions_result['sanctions_hits']}")
                for match in sanctions_result['matches']:
                    if match['type'] == 'sanctions':
                        print(f"  - {match['name']} ({match['source']})")
            elif sanctions_result.get('pep_hits', 0) > 0:
                print(f"⚠ PEP HITS: {sanctions_result['pep_hits']}")
            else:
                print("✓ No sanctions or PEP matches found")

            print(f"  Sources checked: {', '.join(sanctions_result.get('sources_checked', []))}")

        # 3. Offshore Check
        if not output_json:
            print_section("3. OFFSHORE ENTITIES CHECK")
            print("Searching ICIJ Offshore Leaks database...")

        offshore_result = offshore_checker.check(company_name, officers)
        results['offshore'] = offshore_result

        if not output_json:
            if offshore_result.get('offshore_hits', 0) > 0:
                print(f"⚠ OFFSHORE HITS: {offshore_result['offshore_hits']}")
                for match in offshore_result['matches'][:5]:
                    print(f"  - {match['name']}")
                    print(f"    Jurisdiction: {match.get('jurisdiction', 'N/A')}")
                    print(f"    Source: {match.get('source_investigation', 'N/A')}")
            else:
                print("✓ No offshore entity matches found")

        # 4. Trade Activity Check
        if not output_json:
            print_section("4. TRADE ACTIVITY VERIFICATION")
            print("Checking trade records...")

        trade_result = trade_checker.check(
            company_name,
            country_code=country,
            industry_hs_code=hs_code
        )
        results['trade'] = trade_result

        if not output_json:
            if trade_result.get('has_trade_data'):
                volume = trade_result.get('country_trade_volume', 0)
                print(f"  Country trade volume (HS {hs_code}): ${volume:,.0f}")
                if trade_result.get('industry_aligned'):
                    print("  ✓ Trade activity detected in sector")
                else:
                    print("  ⚠ Limited trade in sector")
            else:
                print("  Note: UN Comtrade API not configured or no HS code provided")

            print(f"\n  Manual verification: {trade_result['importyeti_url']}")
            print(f"  {trade_result.get('note', '')}")

        # 5. Risk Scoring
        if not output_json:
            print_section("5. RISK ASSESSMENT")

        risk_assessment = risk_scorer.calculate_score(
            registry_result,
            sanctions_result,
            offshore_result,
            trade_result
        )
        results['risk_assessment'] = risk_assessment

        if not output_json:
            score = risk_assessment['risk_score']
            level = risk_assessment['risk_level']
            confidence = risk_assessment['confidence']

            # Color-coded risk level
            if level == 'HIGH':
                risk_display = f"🔴 HIGH RISK (Score: {score}/100)"
            elif level == 'MEDIUM':
                risk_display = f"🟡 MEDIUM RISK (Score: {score}/100)"
            else:
                risk_display = f"🟢 LOW RISK (Score: {score}/100)"

            print(f"\n{risk_display}")
            print(f"Confidence: {confidence * 100:.0f}%")

            if risk_assessment.get('critical_flags'):
                print("\n⚠ CRITICAL FLAGS:")
                for flag in risk_assessment['critical_flags']:
                    print(f"  • {flag}")

            print("\nRECOMMENDATIONS:")
            for rec in risk_assessment['recommendations']:
                print(f"  {rec}")

            print_section("VERIFICATION COMPLETE")

        return results

    finally:
        # Cleanup
        registry_checker.close()
        sanctions_checker.close()
        trade_checker.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Verify companies for shell company indicators',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python company_verifier.py --name "Apple Inc." --country US
  python company_verifier.py --name "Shell Company Ltd" --country GB --hs-code 85
  python company_verifier.py --name "Test Corp" --country US --json > output.json

Supported Countries:
  US - United States (SEC EDGAR)
  GB - United Kingdom (Companies House)

HS Codes (examples):
  85 - Electronics
  84 - Machinery
  87 - Vehicles
  See: https://www.foreign-trade.com/reference/hscode.htm
        """
    )

    parser.add_argument(
        '--name',
        required=False,
        help='Company name to verify'
    )

    parser.add_argument(
        '--country',
        default='US',
        help='Country code (US, GB, etc.)'
    )

    parser.add_argument(
        '--hs-code',
        help='HS code for trade verification (optional)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    parser.add_argument(
        '--output',
        help='Save results to file'
    )

    parser.add_argument(
        '--check-config',
        action='store_true',
        help='Check API configuration and exit'
    )

    args = parser.parse_args()

    # Check configuration
    if args.check_config:
        print("Checking API configuration...")
        missing = Config.validate()

        print("\nConfigured services:")
        for service in ['opensanctions', 'companies_house', 'comtrade', 'ita']:
            status = "✓" if Config.is_configured(service) else "✗"
            print(f"  {status} {service}")

        if missing:
            print("\nMissing/optional configurations:")
            for key in missing:
                print(f"  - {key}")

        print("\nICIJ data path:", Config.ICIJ_DATA_PATH)
        import os
        if os.path.exists(Config.ICIJ_DATA_PATH):
            print("  ✓ ICIJ data directory exists")
        else:
            print("  ✗ ICIJ data directory not found")

        sys.exit(0)

    # Validate that name is provided for verification
    if not args.name:
        parser.error("--name is required (unless using --check-config)")

    # Run verification
    try:
        results = verify_company(
            company_name=args.name,
            country=args.country.upper(),
            hs_code=args.hs_code,
            output_json=args.json
        )

        # Output JSON
        if args.json:
            print(json.dumps(results, indent=2, default=str))

        # Save to file
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            if not args.json:
                print(f"\nResults saved to: {args.output}")

        # Exit code based on risk level
        risk_level = results.get('risk_assessment', {}).get('risk_level', 'MEDIUM')
        if risk_level == 'HIGH':
            sys.exit(2)
        elif risk_level == 'MEDIUM':
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nVerification cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        if not args.json:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
