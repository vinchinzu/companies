#!/usr/bin/env python3
"""Combine all data sources into unified fraud database.

This script:
1. Extracts data from SEC complaint PDFs
2. Downloads OpenSanctions OFAC data
3. Includes existing SEC EDGAR data
4. Merges everything into a unified database
"""

import json
import os
import sys
from datetime import datetime

import pandas as pd

from scrapers.pdf_extractor import PDFExtractor
from scrapers.opensanctions import OpenSanctionsClient, download_ofac_data
from scrapers.sec_scraper import SECScraper


def extract_from_pdfs() -> list[dict]:
    """Extract fraud cases from all SEC complaint PDFs."""
    print("\n" + "=" * 60)
    print("Extracting from SEC Complaint PDFs...")
    print("=" * 60)

    extractor = PDFExtractor()
    cases = []

    # Find all PDFs
    pdf_dirs = ['data/pdfs', 'data/pdfs/2025', 'data']
    pdfs = []

    for dir_path in pdf_dirs:
        if os.path.exists(dir_path):
            for f in os.listdir(dir_path):
                if f.endswith('.pdf'):
                    path = os.path.join(dir_path, f)
                    if path not in pdfs:
                        pdfs.append(path)

    print(f"Found {len(pdfs)} PDFs")

    for i, pdf_path in enumerate(pdfs, 1):
        try:
            extracted = extractor.extract_case(pdf_path)

            if extracted:
                case_date = extracted.complaint_date or datetime.now().strftime('%Y-%m-%d')
                fraud_type = extracted.fraud_types[0] if extracted.fraud_types else 'SEC Enforcement'

                for defendant in extracted.defendants:
                    if defendant.entity_type == 'company':
                        cases.append({
                            'company_name': defendant.name,
                            'case_date': case_date,
                            'fraud_type': fraud_type,
                            'penalty_amount': extracted.alleged_amount,
                            'jurisdiction': defendant.jurisdiction or '',
                            'source': 'SEC Complaint PDF',
                            'source_url': extracted.source_url or '',
                            'description': f"SEC complaint case {extracted.case_number or ''}",
                            'is_synthetic': False,
                            'case_number': extracted.case_number,
                            'identifiers': json.dumps(defendant.identifiers) if defendant.identifiers else None,
                        })

        except Exception as e:
            print(f"  Error with {pdf_path}: {e}")

    print(f"Extracted {len(cases)} cases from PDFs")
    return cases


def download_opensanctions() -> list[dict]:
    """Download and parse OpenSanctions OFAC data."""
    print("\n" + "=" * 60)
    print("Downloading OpenSanctions OFAC Data...")
    print("=" * 60)

    try:
        cases = download_ofac_data(force=False)
        print(f"Downloaded {len(cases)} sanctioned entities")
        return cases
    except Exception as e:
        print(f"Error downloading OpenSanctions data: {e}")
        return []


def get_sec_known_cases() -> list[dict]:
    """Get known SEC fraud cases from scraper."""
    print("\n" + "=" * 60)
    print("Loading Known SEC Cases...")
    print("=" * 60)

    scraper = SECScraper()
    known = scraper.get_known_cases()

    cases = []
    for case in known:
        cases.append({
            'company_name': case.company_name,
            'case_date': case.case_date,
            'fraud_type': case.fraud_type,
            'penalty_amount': case.penalty_amount,
            'jurisdiction': case.jurisdiction or '',
            'source': case.source,
            'source_url': case.source_url,
            'description': case.description,
            'is_synthetic': case.is_synthetic,
            'case_number': None,
            'identifiers': None,
        })

    print(f"Loaded {len(cases)} known SEC cases")
    return cases


def load_existing_database(filepath: str = 'data/fraudulent_companies.csv') -> pd.DataFrame:
    """Load existing database."""
    if os.path.exists(filepath):
        return pd.read_csv(filepath)
    return pd.DataFrame()


def deduplicate_cases(cases: list[dict]) -> list[dict]:
    """Remove duplicate cases by company name."""
    seen = set()
    unique = []

    for case in cases:
        name_lower = case['company_name'].lower().strip()
        if name_lower not in seen:
            seen.add(name_lower)
            unique.append(case)

    return unique


def main():
    """Main combination process."""
    print("=" * 60)
    print("FRAUD DATABASE COMBINATION TOOL")
    print("Combining all data sources into unified database")
    print("=" * 60)

    all_cases = []

    # 1. Load existing database
    print("\n" + "=" * 60)
    print("Loading Existing Database...")
    print("=" * 60)
    existing_df = load_existing_database()
    if not existing_df.empty:
        existing_cases = existing_df.to_dict('records')
        print(f"Existing database: {len(existing_cases)} records")
        all_cases.extend(existing_cases)

    # 2. Extract from PDFs
    pdf_cases = extract_from_pdfs()
    all_cases.extend(pdf_cases)

    # 3. Download OpenSanctions
    ofac_cases = download_opensanctions()
    all_cases.extend(ofac_cases)

    # 4. Get known SEC cases (in case any were missed)
    sec_cases = get_sec_known_cases()
    all_cases.extend(sec_cases)

    # 5. Deduplicate
    print("\n" + "=" * 60)
    print("Deduplicating Records...")
    print("=" * 60)

    before_count = len(all_cases)
    all_cases = deduplicate_cases(all_cases)
    after_count = len(all_cases)

    print(f"Before dedup: {before_count}")
    print(f"After dedup: {after_count}")
    print(f"Removed: {before_count - after_count} duplicates")

    # 6. Create DataFrame and save
    print("\n" + "=" * 60)
    print("Saving Combined Database...")
    print("=" * 60)

    df = pd.DataFrame(all_cases)

    # Ensure all required columns exist
    required_cols = [
        'company_name', 'case_date', 'fraud_type', 'penalty_amount',
        'jurisdiction', 'source', 'source_url', 'description',
        'is_synthetic', 'case_number', 'identifiers'
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    # Sort by date descending
    df = df.sort_values('case_date', ascending=False)

    # Save
    output_path = 'data/fraudulent_companies.csv'
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} records to {output_path}")

    # Summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"\nTotal records: {len(df)}")

    print(f"\nBy source:")
    source_counts = df['source'].value_counts()
    for source, count in source_counts.items():
        print(f"  {source}: {count}")

    print(f"\nBy fraud type (top 10):")
    type_counts = df['fraud_type'].value_counts().head(10)
    for fraud_type, count in type_counts.items():
        print(f"  {fraud_type}: {count}")

    real_count = len(df[df['is_synthetic'] == False])
    synthetic_count = len(df[df['is_synthetic'] == True])
    print(f"\nReal cases: {real_count}")
    print(f"Synthetic cases: {synthetic_count}")

    return df


if __name__ == '__main__':
    main()
