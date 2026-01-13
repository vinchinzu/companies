#!/usr/bin/env python3
"""Script to compile the fraud dataset."""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.data_compiler import DataCompiler


def main():
    """Compile and save the fraud dataset."""
    compiler = DataCompiler()

    print("Compiling fraud dataset...")
    print("- Including scraped/known cases")
    print("- Generating 60 synthetic shell companies")

    df = compiler.save_dataset(
        filepath="data/fraudulent_companies.csv",
        include_scraped=True,
        include_synthetic=True,
        synthetic_count=60,
    )

    stats = compiler.get_statistics(df)

    print("\n=== Dataset Statistics ===")
    print(f"Total cases: {stats['total_cases']}")
    print(f"Real cases: {stats['real_cases']}")
    print(f"Synthetic cases: {stats['synthetic_cases']}")
    print(f"\nFraud types:")
    for fraud_type, count in stats["fraud_types"].items():
        print(f"  - {fraud_type}: {count}")
    print(f"\nTop jurisdictions:")
    for jur, count in list(stats["jurisdictions"].items())[:10]:
        print(f"  - {jur}: {count}")
    print(f"\nDate range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
    print(f"\nDataset saved to: data/fraudulent_companies.csv")


if __name__ == "__main__":
    main()
