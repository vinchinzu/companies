#!/usr/bin/env python3
"""Extract data from all SEC complaint PDFs and add to fraud database.

This script processes all PDFs in data/pdfs/ directory, extracts case information,
and adds them to the fraudulent_companies.csv database.
"""

import json
import os
import sys
from datetime import datetime

import pandas as pd

from scrapers.pdf_extractor import PDFExtractor


def find_all_pdfs(base_dir: str = 'data/pdfs') -> list[str]:
    """Find all PDF files in directory and subdirectories."""
    pdfs = []

    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.endswith('.pdf'):
                pdfs.append(os.path.join(root, f))

    # Also check for PDFs directly in data/
    data_dir = 'data'
    for f in os.listdir(data_dir):
        if f.endswith('.pdf'):
            path = os.path.join(data_dir, f)
            if path not in pdfs:
                pdfs.append(path)

    return sorted(pdfs)


def extract_to_fraud_cases(pdf_path: str, extractor: PDFExtractor) -> list[dict]:
    """Extract fraud cases from a single PDF.

    Returns list of fraud case dicts for each defendant company.
    """
    cases = []

    try:
        extracted = extractor.extract_case(pdf_path)

        if not extracted:
            return cases

        # Get base case info
        case_date = extracted.complaint_date or datetime.now().strftime('%Y-%m-%d')
        case_number = extracted.case_number
        fraud_types = extracted.fraud_types or ['SEC Enforcement']
        fraud_type = fraud_types[0] if fraud_types else 'SEC Enforcement'

        # Extract defendant companies
        for defendant in extracted.defendants:
            if defendant.entity_type == 'company':
                # Build identifiers dict
                identifiers = defendant.identifiers.copy() if defendant.identifiers else {}

                case = {
                    'company_name': defendant.name,
                    'case_date': case_date,
                    'fraud_type': fraud_type,
                    'penalty_amount': extracted.alleged_amount,
                    'jurisdiction': defendant.jurisdiction or '',
                    'source': 'SEC Complaint PDF',
                    'source_url': extracted.source_url or f'file://{os.path.abspath(pdf_path)}',
                    'description': f"From SEC complaint {case_number or pdf_path}. Court: {extracted.court or 'Unknown'}",
                    'is_synthetic': False,
                    'case_number': case_number,
                    'identifiers': json.dumps(identifiers) if identifiers else None,
                }
                cases.append(case)

        # Also extract relief defendants (often shell companies)
        for defendant in extracted.relief_defendants:
            if defendant.entity_type == 'company':
                case = {
                    'company_name': defendant.name,
                    'case_date': case_date,
                    'fraud_type': fraud_type,
                    'penalty_amount': None,  # Relief defendants usually just have assets frozen
                    'jurisdiction': defendant.jurisdiction or '',
                    'source': 'SEC Complaint PDF',
                    'source_url': extracted.source_url or f'file://{os.path.abspath(pdf_path)}',
                    'description': f"Relief defendant in SEC complaint {case_number or pdf_path}",
                    'is_synthetic': False,
                    'case_number': case_number,
                    'identifiers': json.dumps(defendant.identifiers) if defendant.identifiers else None,
                }
                cases.append(case)

    except Exception as e:
        print(f"  Error extracting {pdf_path}: {e}")

    return cases


def load_existing_database(filepath: str = 'data/fraudulent_companies.csv') -> pd.DataFrame:
    """Load existing fraud database if it exists."""
    if os.path.exists(filepath):
        return pd.read_csv(filepath)
    return pd.DataFrame()


def save_database(df: pd.DataFrame, filepath: str = 'data/fraudulent_companies.csv'):
    """Save fraud database to CSV."""
    df.to_csv(filepath, index=False)
    print(f"Saved {len(df)} records to {filepath}")


def main():
    """Main extraction process."""
    print("=" * 60)
    print("SEC Complaint PDF Extraction")
    print("=" * 60)

    # Find all PDFs
    pdfs = find_all_pdfs()
    print(f"\nFound {len(pdfs)} PDF files")

    if not pdfs:
        print("No PDFs found. Download some first with download_sec_pdfs.py")
        return

    # Initialize extractor
    extractor = PDFExtractor()

    # Load existing database
    existing_df = load_existing_database()
    existing_companies = set()
    if not existing_df.empty and 'company_name' in existing_df.columns:
        existing_companies = set(existing_df['company_name'].str.lower().tolist())

    print(f"Existing database has {len(existing_df)} records")

    # Extract from each PDF
    all_cases = []
    for i, pdf_path in enumerate(pdfs, 1):
        print(f"\n[{i}/{len(pdfs)}] Processing: {os.path.basename(pdf_path)}")

        cases = extract_to_fraud_cases(pdf_path, extractor)

        # Filter out duplicates
        new_cases = []
        for case in cases:
            if case['company_name'].lower() not in existing_companies:
                new_cases.append(case)
                existing_companies.add(case['company_name'].lower())

        if new_cases:
            print(f"  Extracted {len(new_cases)} new companies")
            all_cases.extend(new_cases)
        else:
            print(f"  No new companies (already in database)")

    print(f"\n{'=' * 60}")
    print(f"Extraction Summary")
    print(f"{'=' * 60}")
    print(f"PDFs processed: {len(pdfs)}")
    print(f"New cases extracted: {len(all_cases)}")

    if all_cases:
        # Create DataFrame from new cases
        new_df = pd.DataFrame(all_cases)

        # Combine with existing
        if not existing_df.empty:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        # Save
        save_database(combined_df)

        # Show sample of new cases
        print(f"\nSample of new cases:")
        for case in all_cases[:5]:
            print(f"  - {case['company_name']} ({case['fraud_type']})")
    else:
        print("\nNo new cases to add.")


if __name__ == '__main__':
    main()
