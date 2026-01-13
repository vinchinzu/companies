#!/usr/bin/env python3
"""Import SEC EDGAR enforcement data into the fraud database."""

import json
import re
from pathlib import Path

import pandas as pd


def clean_company_name(name: str) -> str:
    """Clean company name from EDGAR format."""
    # Remove CIK reference
    name = re.sub(r'\s*\(CIK\s+\d+\)', '', name)
    # Remove ticker symbols
    name = re.sub(r'\s*\([A-Z0-9,\s]+\)\s*$', '', name)
    return name.strip()


def main():
    """Import enforcement data to fraud database."""
    enforcement_file = Path("data/sec_enforcement.json")
    db_path = Path("data/fraudulent_companies.csv")

    if not enforcement_file.exists():
        print("No enforcement data found. Run scrape_sec_edgar.py first.")
        return

    # Load enforcement data
    with open(enforcement_file, encoding='utf-8') as f:
        data = json.load(f)

    companies = data.get("companies", [])
    print(f"Loaded {len(companies)} companies from enforcement data")

    # Load existing database
    if db_path.exists():
        df = pd.read_csv(db_path)
        existing_names = set(df["company_name"].str.lower())
        print(f"Existing database has {len(df)} cases")
    else:
        df = pd.DataFrame()
        existing_names = set()

    # Convert to fraud case records
    new_records = []
    for company in companies:
        name = clean_company_name(company.get("company_name", ""))
        if not name or len(name) < 3:
            continue

        # Skip if already in database
        if name.lower() in existing_names:
            continue

        # Map search type to fraud type
        search_types = company.get("search_type", "").split(",")
        fraud_type = "SEC Enforcement"  # Default

        type_mapping = {
            "ponzi_scheme": "Ponzi Scheme",
            "securities_fraud": "Securities Fraud",
            "investment_fraud": "Investment Fraud",
            "wire_fraud": "Wire Fraud",
            "unregistered_securities": "Unregistered Securities",
            "sec_v_cases": "SEC Enforcement",
            "enforcement_action": "SEC Enforcement",
            "revoked": "Registration Revoked",
        }

        for st in search_types:
            if st in type_mapping:
                fraud_type = type_mapping[st]
                break

        record = {
            "company_name": name,
            "case_date": company.get("file_date", ""),
            "fraud_type": fraud_type,
            "penalty_amount": None,
            "jurisdiction": company.get("state", ""),
            "source": "SEC EDGAR",
            "source_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={company.get('cik', '')}",
            "description": f"Found in EDGAR filings via {company.get('search_type', '')} search. Form: {company.get('form_type', '')}",
            "is_synthetic": False,
            "case_number": "",
            "identifiers": json.dumps({"cik": company.get("cik", "")}),
        }

        new_records.append(record)
        existing_names.add(name.lower())

    print(f"Found {len(new_records)} new companies to add")

    if new_records:
        new_df = pd.DataFrame(new_records)
        combined_df = pd.concat([df, new_df], ignore_index=True)
        combined_df = combined_df.sort_values("case_date", ascending=False)
        combined_df = combined_df.reset_index(drop=True)
        combined_df.to_csv(db_path, index=False)

        print(f"\nAdded {len(new_records)} new cases")
        print(f"Total cases in database: {len(combined_df)}")

        # Stats
        real_cases = len(combined_df[~combined_df["is_synthetic"]])
        synthetic_cases = len(combined_df[combined_df["is_synthetic"]])
        print(f"  Real cases: {real_cases}")
        print(f"  Synthetic cases: {synthetic_cases}")

        # Show fraud type breakdown
        print("\nFraud types:")
        print(combined_df["fraud_type"].value_counts().head(15).to_string())
    else:
        print("\nNo new cases to add")


if __name__ == "__main__":
    main()
