"""Data compiler for fraud dataset.

Combines scraped SEC cases, known fraud cases, and synthetic
shell companies into a unified dataset.
"""

import random
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from .sec_scraper import FraudCase, SECScraper


class DataCompiler:
    """Compiles fraud case data from multiple sources."""

    # Synthetic company name components
    PREFIXES = [
        "Global", "Pacific", "Atlantic", "Eastern", "Western",
        "Northern", "Southern", "Premier", "Elite", "Prime",
        "Apex", "Summit", "Pinnacle", "Quantum", "Dynamic",
        "Strategic", "Advanced", "Superior", "Optimal", "Unified",
    ]

    CORE_NAMES = [
        "Capital", "Ventures", "Holdings", "Investments", "Partners",
        "Group", "Solutions", "Enterprises", "International", "Trading",
        "Asset", "Equity", "Finance", "Management", "Consulting",
        "Development", "Resources", "Services", "Industries", "Systems",
    ]

    SUFFIXES = [
        "Ltd.", "LLC", "Inc.", "Corp.", "PTE", "LLP",
        "SA", "AG", "BV", "GmbH", "Sarl", "Limited",
    ]

    # High-risk jurisdiction data
    OFFSHORE_JURISDICTIONS = {
        "ky": {"name": "Cayman Islands", "risk": "high"},
        "vg": {"name": "British Virgin Islands", "risk": "high"},
        "pa": {"name": "Panama", "risk": "high"},
        "bz": {"name": "Belize", "risk": "high"},
        "sc": {"name": "Seychelles", "risk": "high"},
        "bs": {"name": "Bahamas", "risk": "high"},
        "mu": {"name": "Mauritius", "risk": "high"},
        "cy": {"name": "Cyprus", "risk": "medium"},
        "mt": {"name": "Malta", "risk": "medium"},
        "ae": {"name": "UAE", "risk": "medium"},
        "hk": {"name": "Hong Kong", "risk": "medium"},
        "sg": {"name": "Singapore", "risk": "medium"},
    }

    FRAUD_TYPES_SYNTHETIC = [
        "Shell Company Fraud",
        "Money Laundering",
        "Trade-Based Fraud",
        "Investment Fraud",
        "Tax Evasion Vehicle",
    ]

    def __init__(self):
        """Initialize the data compiler."""
        self.scraper = SECScraper()

    def _generate_company_name(self) -> str:
        """Generate a realistic synthetic company name."""
        prefix = random.choice(self.PREFIXES)
        core = random.choice(self.CORE_NAMES)
        suffix = random.choice(self.SUFFIXES)

        patterns = [
            f"{prefix} {core} {suffix}",
            f"{prefix}{core} {suffix}",
            f"{core} {prefix} {suffix}",
        ]

        return random.choice(patterns)

    def _generate_incorporation_date(self, max_age_days: int = 365) -> str:
        """Generate a recent incorporation date (shell companies are often new)."""
        days_ago = random.randint(30, max_age_days)
        date = datetime.now() - timedelta(days=days_ago)
        return date.strftime("%Y-%m-%d")

    def _generate_synthetic_case(self, index: int) -> FraudCase:
        """Generate a synthetic shell company case."""
        jurisdiction = random.choice(list(self.OFFSHORE_JURISDICTIONS.keys()))

        return FraudCase(
            company_name=self._generate_company_name(),
            case_date=self._generate_incorporation_date(max_age_days=730),
            fraud_type=random.choice(self.FRAUD_TYPES_SYNTHETIC),
            penalty_amount=None,
            jurisdiction=jurisdiction,
            source="Synthetic",
            source_url="",
            description=f"Synthetic shell company profile #{index + 1} for demo purposes",
            is_synthetic=True,
        )

    def generate_synthetic_cases(self, count: int = 50) -> list[FraudCase]:
        """Generate synthetic shell company cases."""
        return [self._generate_synthetic_case(i) for i in range(count)]

    def compile_dataset(
        self,
        include_scraped: bool = True,
        include_synthetic: bool = True,
        synthetic_count: int = 50,
    ) -> pd.DataFrame:
        """Compile complete fraud dataset.

        Args:
            include_scraped: Include scraped/known fraud cases
            include_synthetic: Include synthetic shell companies
            synthetic_count: Number of synthetic cases to generate

        Returns:
            DataFrame with all fraud cases
        """
        all_cases = []

        if include_scraped:
            scraped = self.scraper.scrape_all()
            all_cases.extend(scraped)

        if include_synthetic:
            synthetic = self.generate_synthetic_cases(synthetic_count)
            all_cases.extend(synthetic)

        records = [asdict(case) for case in all_cases]
        df = pd.DataFrame(records)

        df = df.sort_values("case_date", ascending=False)
        df = df.reset_index(drop=True)

        return df

    def save_dataset(
        self,
        filepath: str,
        include_scraped: bool = True,
        include_synthetic: bool = True,
        synthetic_count: int = 50,
    ) -> pd.DataFrame:
        """Compile and save dataset to CSV."""
        df = self.compile_dataset(
            include_scraped=include_scraped,
            include_synthetic=include_synthetic,
            synthetic_count=synthetic_count,
        )

        df.to_csv(filepath, index=False)
        return df

    def load_dataset(self, filepath: str) -> pd.DataFrame:
        """Load existing dataset from CSV."""
        return pd.read_csv(filepath)

    def get_statistics(self, df: pd.DataFrame) -> dict:
        """Get dataset statistics."""
        return {
            "total_cases": len(df),
            "real_cases": len(df[~df["is_synthetic"]]),
            "synthetic_cases": len(df[df["is_synthetic"]]),
            "fraud_types": df["fraud_type"].value_counts().to_dict(),
            "jurisdictions": df["jurisdiction"].value_counts().to_dict(),
            "date_range": {
                "earliest": df["case_date"].min(),
                "latest": df["case_date"].max(),
            },
        }
