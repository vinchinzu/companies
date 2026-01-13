#!/usr/bin/env python3
"""Add known SEC cases from pdf_extractor to the fraud database."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from scrapers.pdf_extractor import get_known_cases


def main():
    """Add known SEC cases to the database."""
    db_path = Path("data/fraudulent_companies.csv")

    print("=" * 60)
    print("Adding Known SEC Cases to Database")
    print("=" * 60)

    # Get known cases
    known_cases = get_known_cases()
    print(f"Found {len(known_cases)} known SEC cases")

    # Convert to fraud case records
    all_records = []
    for case in known_cases:
        records = case.to_fraud_cases()
        all_records.extend(records)

    print(f"Converted to {len(all_records)} company records")

    # Load existing database
    if db_path.exists():
        df = pd.read_csv(db_path)
        print(f"Loaded existing database with {len(df)} cases")
    else:
        df = pd.DataFrame()
        print("Creating new database")

    # Convert new records to DataFrame
    new_df = pd.DataFrame(all_records)

    # Ensure required columns exist
    for col in ["company_name", "case_date", "fraud_type", "penalty_amount",
                "jurisdiction", "source", "source_url", "description", "is_synthetic"]:
        if col not in new_df.columns:
            new_df[col] = None

    # Deduplicate by company name (case insensitive)
    existing_names = set(df["company_name"].str.lower()) if len(df) > 0 else set()
    unique_records = []

    for _, row in new_df.iterrows():
        name_lower = row["company_name"].lower()
        if name_lower not in existing_names:
            unique_records.append(row.to_dict())
            existing_names.add(name_lower)
        else:
            print(f"  Skipping duplicate: {row['company_name']}")

    if unique_records:
        unique_df = pd.DataFrame(unique_records)
        combined_df = pd.concat([df, unique_df], ignore_index=True)
        combined_df = combined_df.sort_values("case_date", ascending=False)
        combined_df = combined_df.reset_index(drop=True)
        combined_df.to_csv(db_path, index=False)

        print(f"\nAdded {len(unique_records)} new cases")
        print(f"Total cases in database: {len(combined_df)}")

        # Show some stats
        real_cases = len(combined_df[~combined_df["is_synthetic"]])
        synthetic_cases = len(combined_df[combined_df["is_synthetic"]])
        print(f"  Real cases: {real_cases}")
        print(f"  Synthetic cases: {synthetic_cases}")
    else:
        print("\nNo new cases to add (all duplicates)")


if __name__ == "__main__":
    main()
