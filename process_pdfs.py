#!/usr/bin/env python3
"""Script to process SEC complaint PDFs and add extracted entities to the database."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from scrapers.pdf_extractor import PDFExtractor, get_known_cases


def process_all_pdfs(pdf_dir: str = "data/pdfs") -> list[dict]:
    """Process all PDFs in directory and extract fraud cases.

    Args:
        pdf_dir: Directory containing PDFs to process

    Returns:
        List of fraud case dictionaries
    """
    extractor = PDFExtractor(pdf_dir)
    all_cases = []

    # Get pre-populated known cases first
    known = get_known_cases()
    for case in known:
        fraud_cases = case.to_fraud_cases()
        all_cases.extend(fraud_cases)
        print(f"Added known case: {case.case_title}")
        for fc in fraud_cases:
            print(f"  - {fc['company_name']} ({fc['jurisdiction']})")

    # Process any PDFs in the directory
    pdf_path = Path(pdf_dir)
    if pdf_path.exists():
        for pdf_file in pdf_path.glob("*.pdf"):
            # Skip if it's actually HTML (failed download)
            with open(pdf_file, "rb") as f:
                header = f.read(10)
                if not header.startswith(b"%PDF"):
                    print(f"Skipping {pdf_file.name} (not a valid PDF)")
                    continue

            print(f"\nProcessing: {pdf_file.name}")
            try:
                case = extractor.extract_case(pdf_file)
                fraud_cases = case.to_fraud_cases()
                all_cases.extend(fraud_cases)

                print(f"  Case: {case.case_number}")
                print(f"  Fraud types: {', '.join(case.fraud_types)}")
                print(f"  Extracted {len(case.defendants)} defendants")
                for fc in fraud_cases:
                    print(f"    - {fc['company_name']}")

            except Exception as e:
                print(f"  Error processing {pdf_file.name}: {e}")

    return all_cases


def add_to_database(
    new_cases: list[dict],
    db_path: str = "data/fraudulent_companies.csv",
) -> pd.DataFrame:
    """Add extracted cases to the fraud database.

    Args:
        new_cases: List of new fraud case dictionaries
        db_path: Path to the database CSV

    Returns:
        Updated DataFrame
    """
    # Load existing database
    if os.path.exists(db_path):
        df = pd.read_csv(db_path)
        print(f"\nLoaded existing database with {len(df)} cases")
    else:
        df = pd.DataFrame()
        print("\nCreating new database")

    # Convert new cases to DataFrame
    if not new_cases:
        print("No new cases to add")
        return df

    new_df = pd.DataFrame(new_cases)

    # Ensure required columns exist
    required_cols = [
        "company_name", "case_date", "fraud_type", "penalty_amount",
        "jurisdiction", "source", "source_url", "description", "is_synthetic"
    ]

    for col in required_cols:
        if col not in new_df.columns:
            new_df[col] = None

    # Check for duplicates by company name
    existing_names = set(df["company_name"].str.lower()) if len(df) > 0 else set()
    unique_cases = []

    for _, row in new_df.iterrows():
        if row["company_name"].lower() not in existing_names:
            unique_cases.append(row.to_dict())
            existing_names.add(row["company_name"].lower())
        else:
            print(f"  Skipping duplicate: {row['company_name']}")

    if not unique_cases:
        print("All cases already in database")
        return df

    unique_df = pd.DataFrame(unique_cases)

    # Combine with existing
    combined_df = pd.concat([df, unique_df], ignore_index=True)

    # Sort by date
    combined_df = combined_df.sort_values("case_date", ascending=False)
    combined_df = combined_df.reset_index(drop=True)

    # Save
    combined_df.to_csv(db_path, index=False)
    print(f"\nAdded {len(unique_cases)} new cases")
    print(f"Total cases in database: {len(combined_df)}")

    return combined_df


def main():
    """Main function to process PDFs and update database."""
    print("=" * 60)
    print("SEC Complaint PDF Processor")
    print("=" * 60)

    # Process PDFs
    cases = process_all_pdfs()

    # Add to database
    df = add_to_database(cases)

    # Print summary
    print("\n" + "=" * 60)
    print("Database Summary")
    print("=" * 60)

    if len(df) > 0:
        print(f"Total cases: {len(df)}")
        print(f"Real cases: {len(df[~df['is_synthetic']])}")
        print(f"Synthetic cases: {len(df[df['is_synthetic']])}")

        print("\nRecent additions from SEC complaints:")
        sec_cases = df[df["source"] == "SEC Complaint"]
        if len(sec_cases) > 0:
            for _, row in sec_cases.head(10).iterrows():
                print(f"  - {row['company_name']} ({row['jurisdiction']}): {row['fraud_type']}")
        else:
            print("  (none)")


if __name__ == "__main__":
    main()
