"""ICIJ Offshore Leaks Database Integration.

Downloads and parses data from the ICIJ Offshore Leaks database
containing 810,000+ offshore entities from Panama Papers, Paradise Papers,
Pandora Papers, and other investigations.
"""

import csv
import io
import os
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Iterator

import requests


@dataclass
class OffshoreEntity:
    """Represents an offshore entity from ICIJ database."""

    node_id: str
    name: str
    entity_type: str  # 'Entity', 'Officer', 'Intermediary', 'Address'
    jurisdiction: Optional[str] = None
    jurisdiction_description: Optional[str] = None
    country_codes: Optional[str] = None
    countries: Optional[str] = None
    source_id: Optional[str] = None  # Which leak (Panama, Paradise, etc.)
    valid_until: Optional[str] = None
    note: Optional[str] = None
    address: Optional[str] = None
    incorporation_date: Optional[str] = None
    inactivation_date: Optional[str] = None
    struck_off_date: Optional[str] = None
    status: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'node_id': self.node_id,
            'name': self.name,
            'entity_type': self.entity_type,
            'jurisdiction': self.jurisdiction,
            'jurisdiction_description': self.jurisdiction_description,
            'country_codes': self.country_codes,
            'countries': self.countries,
            'source_id': self.source_id,
            'valid_until': self.valid_until,
            'note': self.note,
            'address': self.address,
            'incorporation_date': self.incorporation_date,
            'inactivation_date': self.inactivation_date,
            'struck_off_date': self.struck_off_date,
            'status': self.status,
        }


class ICIJOffshoreClient:
    """Client for downloading and parsing ICIJ Offshore Leaks data."""

    # Download URLs
    CSV_URL = "https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip"

    # Source ID mapping to investigation name
    SOURCES = {
        'Panama Papers': 'panama_papers',
        'Paradise Papers': 'paradise_papers',
        'Pandora Papers': 'pandora_papers',
        'Offshore Leaks': 'offshore_leaks',
        'Bahamas Leaks': 'bahamas_leaks',
    }

    HEADERS = {
        'User-Agent': 'CompanyResearchTool/1.0 (Research)',
        'Accept': '*/*',
    }

    def __init__(self, cache_dir: str = 'data/icij'):
        """Initialize client with cache directory."""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _get_cache_path(self, filename: str) -> str:
        """Get cache file path."""
        return os.path.join(self.cache_dir, filename)

    def download_database(self, force: bool = False) -> Optional[str]:
        """Download the full ICIJ offshore database.

        Args:
            force: Force re-download even if cached

        Returns:
            Path to extracted directory or None if failed
        """
        zip_path = self._get_cache_path('full-oldb.zip')
        extract_dir = self._get_cache_path('csv')

        # Check cache
        if not force and os.path.exists(extract_dir):
            csv_files = [f for f in os.listdir(extract_dir) if f.endswith('.csv')]
            if csv_files:
                print(f"Using cached ICIJ data: {extract_dir}")
                return extract_dir

        # Download
        print(f"Downloading ICIJ Offshore Leaks database...")
        print(f"URL: {self.CSV_URL}")
        print("This may take several minutes (100+ MB download)...")

        try:
            response = self.session.get(self.CSV_URL, stream=True, timeout=600)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            pct = (downloaded / total_size) * 100
                            mb = downloaded / (1024 * 1024)
                            print(f"\rDownloaded: {mb:.1f} MB ({pct:.1f}%)", end='', flush=True)

            print(f"\nDownload complete: {zip_path}")

            # Extract
            print("Extracting ZIP file...")
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)

            print(f"Extracted to: {extract_dir}")

            # List contents
            files = os.listdir(extract_dir)
            print(f"Files: {files}")

            return extract_dir

        except requests.RequestException as e:
            print(f"Download failed: {e}")
            return None
        except zipfile.BadZipFile as e:
            print(f"Invalid ZIP file: {e}")
            return None

    def _parse_csv(self, filepath: str, entity_type: str) -> Iterator[OffshoreEntity]:
        """Parse a CSV file and yield entities."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    yield OffshoreEntity(
                        node_id=row.get('node_id', ''),
                        name=row.get('name', ''),
                        entity_type=entity_type,
                        jurisdiction=row.get('jurisdiction', ''),
                        jurisdiction_description=row.get('jurisdiction_description', ''),
                        country_codes=row.get('country_codes', ''),
                        countries=row.get('countries', ''),
                        source_id=row.get('sourceID', ''),
                        valid_until=row.get('valid_until', ''),
                        note=row.get('note', ''),
                        address=row.get('address', ''),
                        incorporation_date=row.get('incorporation_date', ''),
                        inactivation_date=row.get('inactivation_date', ''),
                        struck_off_date=row.get('struck_off_date', ''),
                        status=row.get('status', ''),
                    )

        except IOError as e:
            print(f"Error reading {filepath}: {e}")

    def get_entities(self, data_dir: str = None,
                     entity_types: list = None) -> Iterator[OffshoreEntity]:
        """Get offshore entities from the database.

        Args:
            data_dir: Path to extracted CSV directory
            entity_types: List of types to include ['Entity', 'Officer', 'Intermediary']

        Yields:
            OffshoreEntity objects
        """
        if data_dir is None:
            data_dir = self._get_cache_path('csv')

        if not os.path.exists(data_dir):
            print("ICIJ data not found. Run download_database() first.")
            return

        # Default to all types
        if entity_types is None:
            entity_types = ['Entity', 'Officer', 'Intermediary', 'Address']

        # Map entity types to CSV files
        file_map = {
            'Entity': 'nodes-entities.csv',
            'Officer': 'nodes-officers.csv',
            'Intermediary': 'nodes-intermediaries.csv',
            'Address': 'nodes-addresses.csv',
        }

        for etype in entity_types:
            if etype in file_map:
                filepath = os.path.join(data_dir, file_map[etype])
                if os.path.exists(filepath):
                    print(f"Loading {etype} data from {filepath}...")
                    yield from self._parse_csv(filepath, etype)

    def get_entity_names(self, data_dir: str = None) -> set:
        """Get set of all entity names for quick lookup.

        Args:
            data_dir: Path to extracted CSV directory

        Returns:
            Set of lowercase entity names
        """
        names = set()

        for entity in self.get_entities(data_dir, entity_types=['Entity']):
            if entity.name:
                names.add(entity.name.lower().strip())

        return names

    def build_names_file(self, output_path: str = None) -> str:
        """Build a names-only text file for fast lookups.

        Args:
            output_path: Path for output file

        Returns:
            Path to created file
        """
        if output_path is None:
            output_path = self._get_cache_path('offshore_names.txt')

        print("Building offshore entity names file...")

        count = 0
        with open(output_path, 'w', encoding='utf-8') as f:
            for entity in self.get_entities(entity_types=['Entity']):
                if entity.name:
                    f.write(entity.name + '\n')
                    count += 1

                    if count % 100000 == 0:
                        print(f"  Processed {count:,} entities...")

        print(f"Created {output_path} with {count:,} names")
        return output_path

    def check_company(self, company_name: str, names_file: str = None) -> dict:
        """Check if a company name appears in offshore leaks.

        Args:
            company_name: Name to check
            names_file: Path to names file (builds if not exists)

        Returns:
            Dict with match results
        """
        if names_file is None:
            names_file = self._get_cache_path('offshore_names.txt')

        # Build names file if needed
        if not os.path.exists(names_file):
            self.build_names_file(names_file)

        # Load names
        names = set()
        with open(names_file, 'r', encoding='utf-8') as f:
            names = {line.strip().lower() for line in f if line.strip()}

        company_lower = company_name.lower().strip()

        # Exact match
        if company_lower in names:
            return {
                'match': True,
                'match_type': 'exact',
                'database': 'ICIJ Offshore Leaks',
                'confidence': 1.0,
            }

        # Partial match
        for name in names:
            if len(company_lower) > 5 and (company_lower in name or name in company_lower):
                return {
                    'match': True,
                    'match_type': 'partial',
                    'matched_name': name,
                    'database': 'ICIJ Offshore Leaks',
                    'confidence': 0.7,
                }

        return {
            'match': False,
            'match_type': None,
            'database': 'ICIJ Offshore Leaks',
            'confidence': 0.0,
        }

    def get_statistics(self, data_dir: str = None) -> dict:
        """Get statistics about the downloaded data.

        Args:
            data_dir: Path to extracted CSV directory

        Returns:
            Dict with counts and statistics
        """
        if data_dir is None:
            data_dir = self._get_cache_path('csv')

        stats = {
            'entities': 0,
            'officers': 0,
            'intermediaries': 0,
            'addresses': 0,
            'jurisdictions': set(),
            'sources': set(),
        }

        for entity in self.get_entities(data_dir):
            if entity.entity_type == 'Entity':
                stats['entities'] += 1
            elif entity.entity_type == 'Officer':
                stats['officers'] += 1
            elif entity.entity_type == 'Intermediary':
                stats['intermediaries'] += 1
            elif entity.entity_type == 'Address':
                stats['addresses'] += 1

            if entity.jurisdiction:
                stats['jurisdictions'].add(entity.jurisdiction)
            if entity.source_id:
                stats['sources'].add(entity.source_id)

        stats['jurisdictions'] = len(stats['jurisdictions'])
        stats['sources'] = list(stats['sources'])

        return stats


def download_icij_data(force: bool = False) -> bool:
    """Convenience function to download ICIJ data.

    Args:
        force: Force re-download

    Returns:
        True if successful
    """
    client = ICIJOffshoreClient()
    result = client.download_database(force=force)
    return result is not None


if __name__ == '__main__':
    print("ICIJ Offshore Leaks Database Client")
    print("=" * 50)

    client = ICIJOffshoreClient()

    # Check if data exists
    csv_dir = client._get_cache_path('csv')
    if os.path.exists(csv_dir):
        print(f"\nData directory exists: {csv_dir}")
        files = os.listdir(csv_dir)
        print(f"Files: {files}")

        # Show stats (sample only to avoid long runtime)
        print("\nSample entities:")
        count = 0
        for entity in client.get_entities(entity_types=['Entity']):
            print(f"  - {entity.name} ({entity.jurisdiction})")
            count += 1
            if count >= 5:
                break
    else:
        print("\nICIJ data not downloaded yet.")
        print("Run: python -c \"from scrapers.icij_offshore import download_icij_data; download_icij_data()\"")
