#!/usr/bin/env python3
"""Create a sample input Excel file for testing."""

import pandas as pd


def main():
    """Create sample input file with test companies."""
    companies = [
        {"Company Name": "Apple Inc.", "Jurisdiction": "us_ca"},
        {"Company Name": "Microsoft Corporation", "Jurisdiction": "us_wa"},
        {"Company Name": "Alphabet Inc.", "Jurisdiction": "us_ca"},
        {"Company Name": "Amazon.com, Inc.", "Jurisdiction": "us_wa"},
        {"Company Name": "Tesla, Inc.", "Jurisdiction": "us_tx"},
        {"Company Name": "Meta Platforms, Inc.", "Jurisdiction": "us_ca"},
        {"Company Name": "Nvidia Corporation", "Jurisdiction": "us_ca"},
        {"Company Name": "JPMorgan Chase & Co.", "Jurisdiction": "us_ny"},
        {"Company Name": "Visa Inc.", "Jurisdiction": "us_ca"},
        {"Company Name": "Walmart Inc.", "Jurisdiction": "us_ar"},
        # Some suspicious-looking companies for testing
        {"Company Name": "Global Apex Holdings Ltd.", "Jurisdiction": "ky"},
        {"Company Name": "Pacific Ventures PTE", "Jurisdiction": "sg"},
        {"Company Name": "Premier Capital Solutions LLC", "Jurisdiction": "us_de"},
        {"Company Name": "Eastern Trading International", "Jurisdiction": "hk"},
        {"Company Name": "Summit Asset Management SA", "Jurisdiction": "pa"},
    ]

    df = pd.DataFrame(companies)
    df.to_excel("data/sample_input.xlsx", index=False)
    print(f"Created sample input file with {len(df)} companies")
    print("Saved to: data/sample_input.xlsx")


if __name__ == "__main__":
    main()
