"""OpenSanctions Data Integration.

Downloads and parses data from OpenSanctions OFAC press releases dataset
for sanctions and KYC compliance data.
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import requests


@dataclass
class SanctionedEntity:
    """Represents a sanctioned entity from OpenSanctions."""

    name: str
    entity_type: str  # 'company', 'individual', 'organization', 'vessel', 'aircraft'
    country: Optional[str]
    aliases: list[str] = field(default_factory=list)
    identifiers: dict = field(default_factory=dict)  # Tax IDs, registration numbers, etc.
    sanctions_program: Optional[str] = None
    listing_date: Optional[str] = None
    source_url: Optional[str] = None
    description: Optional[str] = None
    addresses: list[str] = field(default_factory=list)

    def to_fraud_case_dict(self) -> dict:
        """Convert to fraud case format for database integration."""
        return {
            'company_name': self.name,
            'case_date': self.listing_date or datetime.now().strftime('%Y-%m-%d'),
            'fraud_type': 'OFAC Sanctions',
            'penalty_amount': None,
            'jurisdiction': self.country,
            'source': 'OpenSanctions/OFAC',
            'source_url': self.source_url or 'https://www.opensanctions.org/datasets/us_ofac_press_releases/',
            'description': self.description or f'{self.entity_type.title()} sanctioned under {self.sanctions_program or "OFAC program"}',
            'is_synthetic': False,
            'case_number': None,
            'identifiers': json.dumps(self.identifiers) if self.identifiers else None,
        }


class OpenSanctionsClient:
    """Client for downloading and parsing OpenSanctions data."""

    BASE_URL = "https://data.opensanctions.org/datasets/latest"
    DATASETS = {
        'ofac_press_releases': 'us_ofac_press_releases',
        'ofac_sdn': 'us_ofac_sdn',  # SDN (Specially Designated Nationals)
        'ofac_cons': 'us_ofac_cons',  # Consolidated list
        'eu_sanctions': 'eu_fsf',
        'un_sanctions': 'un_sc_sanctions',
    }

    HEADERS = {
        'User-Agent': 'CompanyResearchTool/1.0 (Research Bot)',
        'Accept': 'application/json',
    }

    def __init__(self, cache_dir: str = 'data/opensanctions'):
        """Initialize client with cache directory."""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _get_cache_path(self, dataset: str, format: str = 'json') -> str:
        """Get cache file path for dataset."""
        return os.path.join(self.cache_dir, f'{dataset}.{format}')

    def _download_file(self, url: str, dest_path: str) -> bool:
        """Download file from URL to destination path."""
        try:
            print(f"Downloading {url}...")
            response = self.session.get(url, stream=True, timeout=120)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            pct = (downloaded / total_size) * 100
                            print(f"\rProgress: {pct:.1f}%", end='', flush=True)

            print(f"\nDownloaded to {dest_path}")
            return True

        except requests.RequestException as e:
            print(f"Download failed: {e}")
            return False

    def download_dataset(self, dataset_key: str = 'ofac_press_releases',
                         force: bool = False) -> Optional[str]:
        """Download a dataset from OpenSanctions.

        Args:
            dataset_key: Key from DATASETS dict
            force: Force re-download even if cached

        Returns:
            Path to downloaded file or None if failed
        """
        if dataset_key not in self.DATASETS:
            print(f"Unknown dataset: {dataset_key}. Available: {list(self.DATASETS.keys())}")
            return None

        dataset_name = self.DATASETS[dataset_key]
        cache_path = self._get_cache_path(dataset_name, 'json')

        # Check cache
        if not force and os.path.exists(cache_path):
            # Check if file is less than 24 hours old
            file_age = time.time() - os.path.getmtime(cache_path)
            if file_age < 86400:  # 24 hours
                print(f"Using cached data: {cache_path}")
                return cache_path

        # Download FTM (Follow The Money) format - most complete
        url = f"{self.BASE_URL}/{dataset_name}/entities.ftm.json"

        if self._download_file(url, cache_path):
            return cache_path

        return None

    def download_names_list(self, dataset_key: str = 'ofac_press_releases') -> Optional[str]:
        """Download just the names text file (smaller, faster)."""
        if dataset_key not in self.DATASETS:
            return None

        dataset_name = self.DATASETS[dataset_key]
        cache_path = self._get_cache_path(dataset_name, 'names.txt')

        url = f"{self.BASE_URL}/{dataset_name}/names.txt"

        if self._download_file(url, cache_path):
            return cache_path
        return None

    def parse_ftm_entities(self, filepath: str) -> list[SanctionedEntity]:
        """Parse FTM JSON format entities.

        FTM (Follow The Money) is a structured format for entity data.
        """
        entities = []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        entity = self._parse_ftm_entity(data)
                        if entity:
                            entities.append(entity)
                    except json.JSONDecodeError:
                        continue

        except IOError as e:
            print(f"Error reading file: {e}")

        return entities

    def _parse_ftm_entity(self, data: dict) -> Optional[SanctionedEntity]:
        """Parse a single FTM entity record."""
        schema = data.get('schema', '')
        properties = data.get('properties', {})

        # Map FTM schema to entity type
        type_map = {
            'Company': 'company',
            'Organization': 'organization',
            'Person': 'individual',
            'LegalEntity': 'company',
            'Vessel': 'vessel',
            'Aircraft': 'aircraft',
            'Article': 'article',
        }

        entity_type = type_map.get(schema, 'unknown')

        # Skip articles and unknown types for fraud database
        if entity_type in ('article', 'unknown'):
            return None

        # Get primary name
        names = properties.get('name', [])
        if not names:
            return None

        name = names[0]
        aliases = names[1:] if len(names) > 1 else []

        # Get country
        countries = properties.get('country', [])
        country = countries[0] if countries else None

        # Get identifiers
        identifiers = {}
        for id_type in ['registrationNumber', 'taxNumber', 'innCode', 'imoNumber',
                        'callSign', 'mmsi', 'passportNumber', 'idNumber']:
            values = properties.get(id_type, [])
            if values:
                identifiers[id_type] = values[0] if len(values) == 1 else values

        # Get addresses
        addresses = properties.get('address', [])

        # Get listing date
        dates = properties.get('createdAt', []) or properties.get('modifiedAt', [])
        listing_date = dates[0][:10] if dates else None

        # Get source URL
        source_urls = properties.get('sourceUrl', [])
        source_url = source_urls[0] if source_urls else None

        # Get description/notes
        notes = properties.get('notes', [])
        description = notes[0] if notes else None

        # Get sanctions program
        programs = properties.get('program', []) or properties.get('topics', [])
        program = programs[0] if programs else 'OFAC'

        return SanctionedEntity(
            name=name,
            entity_type=entity_type,
            country=country,
            aliases=aliases,
            identifiers=identifiers,
            sanctions_program=program,
            listing_date=listing_date,
            source_url=source_url,
            description=description,
            addresses=addresses,
        )

    def get_companies(self, filepath: str = None,
                      download_if_missing: bool = True) -> list[SanctionedEntity]:
        """Get only company/organization entities.

        Args:
            filepath: Path to cached file, or None to auto-download
            download_if_missing: Whether to download if not cached

        Returns:
            List of company/organization entities
        """
        if filepath is None:
            filepath = self._get_cache_path(self.DATASETS['ofac_press_releases'], 'json')

            if not os.path.exists(filepath) and download_if_missing:
                filepath = self.download_dataset('ofac_press_releases')

            if not filepath:
                return []

        entities = self.parse_ftm_entities(filepath)
        return [e for e in entities if e.entity_type in ('company', 'organization')]

    def get_all_sanctioned_names(self, dataset_key: str = 'ofac_press_releases') -> set[str]:
        """Get set of all sanctioned entity names for quick lookup."""
        filepath = self.download_names_list(dataset_key)
        if not filepath:
            return set()

        names = set()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    name = line.strip()
                    if name:
                        names.add(name.lower())
        except IOError:
            pass

        return names

    def check_against_sanctions(self, company_name: str,
                                threshold: float = 0.8) -> dict:
        """Check if a company name matches any sanctioned entities.

        Args:
            company_name: Name to check
            threshold: Fuzzy match threshold (0-1)

        Returns:
            Dict with match results
        """
        names = self.get_all_sanctioned_names()

        company_lower = company_name.lower().strip()

        # Exact match
        if company_lower in names:
            return {
                'match': True,
                'match_type': 'exact',
                'matched_name': company_name,
                'confidence': 1.0,
            }

        # Partial match (contains)
        for name in names:
            if company_lower in name or name in company_lower:
                return {
                    'match': True,
                    'match_type': 'partial',
                    'matched_name': name,
                    'confidence': 0.8,
                }

        return {
            'match': False,
            'match_type': None,
            'matched_name': None,
            'confidence': 0.0,
        }

    def to_fraud_cases(self, entities: list[SanctionedEntity] = None) -> list[dict]:
        """Convert entities to fraud case format for database.

        Args:
            entities: List of entities, or None to auto-download

        Returns:
            List of dicts in fraud case format
        """
        if entities is None:
            entities = self.get_companies()

        return [e.to_fraud_case_dict() for e in entities]


def download_ofac_data(force: bool = False) -> list[dict]:
    """Convenience function to download OFAC data and return fraud cases.

    Args:
        force: Force re-download even if cached

    Returns:
        List of fraud case dicts
    """
    client = OpenSanctionsClient()
    filepath = client.download_dataset('ofac_press_releases', force=force)

    if not filepath:
        print("Failed to download OFAC data")
        return []

    entities = client.get_companies(filepath)
    print(f"Parsed {len(entities)} company/organization entities")

    return client.to_fraud_cases(entities)


if __name__ == '__main__':
    # Test the client
    print("Testing OpenSanctions client...")

    client = OpenSanctionsClient()

    # Download OFAC press releases
    filepath = client.download_dataset('ofac_press_releases')

    if filepath:
        # Parse entities
        entities = client.parse_ftm_entities(filepath)
        print(f"\nTotal entities: {len(entities)}")

        # Count by type
        by_type = {}
        for e in entities:
            by_type[e.entity_type] = by_type.get(e.entity_type, 0) + 1

        print("\nBy type:")
        for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"  {t}: {count}")

        # Show sample companies
        companies = [e for e in entities if e.entity_type == 'company']
        print(f"\nSample companies ({len(companies)} total):")
        for c in companies[:5]:
            print(f"  - {c.name} ({c.country})")
            if c.aliases:
                print(f"    Aliases: {c.aliases[:3]}")
