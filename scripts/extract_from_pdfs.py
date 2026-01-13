#!/usr/bin/env python3
"""Extract entities from downloaded SEC complaint PDFs and add to database."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from scrapers.pdf_extractor import PDFExtractor


def main():
    """Extract entities from PDFs and update database."""
    pdf_dir = Path("data/pdfs/2025")
    db_path = Path("data/fraudulent_companies.csv")

    print("=" * 60)
    print("SEC PDF Entity Extractor")
    print("=" * 60)

    extractor = PDFExtractor(str(pdf_dir))

    # Find all valid PDFs
    pdfs = []
    for pdf_file in pdf_dir.glob("*.pdf"):
        with open(pdf_file, "rb") as f:
            if f.read(4) == b"%PDF":
                pdfs.append(pdf_file)

    print(f"Found {len(pdfs)} valid PDFs to process")

    # Process each PDF
    all_cases = []
    for pdf_file in sorted(pdfs):
        print(f"\nProcessing: {pdf_file.name}")
        try:
            case = extractor.extract_case(
                pdf_file,
                source_url=f"https://www.sec.gov/files/litigation/complaints/2025/{pdf_file.name}"
            )

            print(f"  Case: {case.case_number or 'Unknown'}")
            print(f"  Court: {case.court or 'Unknown'}")
            print(f"  Date: {case.complaint_date or 'Unknown'}")
            print(f"  Fraud types: {case.fraud_types}")
            print(f"  Amount: ${case.alleged_amount:,.0f}" if case.alleged_amount else "  Amount: Unknown")
            print(f"  Defendants: {len(case.defendants)}")

            for defendant in case.defendants:
                print(f"    - {defendant.name} ({defendant.entity_type}, {defendant.jurisdiction or 'unknown'})")
                if defendant.identifiers:
                    print(f"      IDs: {defendant.identifiers}")

            # Convert to fraud cases
            fraud_cases = case.to_fraud_cases()
            all_cases.extend(fraud_cases)

        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\n{'=' * 60}")
    print(f"Extracted {len(all_cases)} company records from PDFs")

    if not all_cases:
        print("No cases to add")
        return

    # Load existing database
    if db_path.exists():
        df = pd.read_csv(db_path)
        print(f"Loaded existing database with {len(df)} cases")
    else:
        df = pd.DataFrame()

    # Convert new cases
    new_df = pd.DataFrame(all_cases)

    # Ensure columns
    for col in ["company_name", "case_date", "fraud_type", "penalty_amount",
                "jurisdiction", "source", "source_url", "description", "is_synthetic"]:
        if col not in new_df.columns:
            new_df[col] = None

    # Deduplicate
    existing_names = set(df["company_name"].str.lower()) if len(df) > 0 else set()
    unique_cases = []

    for _, row in new_df.iterrows():
        name_lower = row["company_name"].lower()
        if name_lower not in existing_names:
            unique_cases.append(row.to_dict())
            existing_names.add(name_lower)
        else:
            print(f"  Skipping duplicate: {row['company_name']}")

    if unique_cases:
        unique_df = pd.DataFrame(unique_cases)
        combined_df = pd.concat([df, unique_df], ignore_index=True)
        combined_df = combined_df.sort_values("case_date", ascending=False)
        combined_df = combined_df.reset_index(drop=True)
        combined_df.to_csv(db_path, index=False)

        print(f"\nAdded {len(unique_cases)} new cases from PDFs")
        print(f"Total cases in database: {len(combined_df)}")
    else:
        print("\nNo new cases to add (all duplicates)")


if __name__ == "__main__":
    main()
