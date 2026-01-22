"""
Offshore entities checker module.
Searches ICIJ Offshore Leaks database for shell company indicators.
"""

import os
from typing import Dict, Any, List
import pandas as pd
from utils.helpers import normalize_company_name, is_tax_haven
from config import Config


class OffshoreChecker:
    """Check for offshore entity matches in ICIJ Offshore Leaks database."""

    def __init__(self):
        """Initialize offshore checker with ICIJ data."""
        self.entities_df = None
        self.officers_df = None
        self.relationships_df = None
        self.data_loaded = False

        self._load_data()

    def _load_data(self):
        """Load ICIJ CSV files if available."""
        data_path = Config.ICIJ_DATA_PATH

        if not os.path.exists(data_path):
            print(f"Warning: ICIJ data path not found: {data_path}")
            print("To use offshore checking, download from: https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip")
            return

        # Define CSV file paths
        entities_file = os.path.join(data_path, 'nodes-entities.csv')
        officers_file = os.path.join(data_path, 'nodes-officers.csv')
        relationships_file = os.path.join(data_path, 'relationships.csv')

        try:
            # Load entities (companies, trusts, etc.)
            if os.path.exists(entities_file):
                self.entities_df = pd.read_csv(entities_file, low_memory=False)
                print(f"Loaded {len(self.entities_df)} offshore entities")

            # Load officers (individuals)
            if os.path.exists(officers_file):
                self.officers_df = pd.read_csv(officers_file, low_memory=False)
                print(f"Loaded {len(self.officers_df)} offshore officers")

            # Load relationships
            if os.path.exists(relationships_file):
                self.relationships_df = pd.read_csv(relationships_file, low_memory=False)
                print(f"Loaded {len(self.relationships_df)} offshore relationships")

            self.data_loaded = True

        except Exception as e:
            print(f"Error loading ICIJ data: {e}")
            self.data_loaded = False

    def check(self, company_name: str, officers: List[str] = None) -> Dict[str, Any]:
        """
        Check for offshore entity matches.

        Args:
            company_name: Company name to search
            officers: List of officer names to search

        Returns:
            Offshore checking results
        """
        if not self.data_loaded:
            return {
                'offshore_hits': 0,
                'matches': [],
                'jurisdictions': [],
                'red_flags': ['ICIJ data not loaded'],
                'confidence': 0.0
            }

        results = {
            'offshore_hits': 0,
            'matches': [],
            'jurisdictions': [],
            'red_flags': [],
            'confidence': 1.0
        }

        # Search entities
        if self.entities_df is not None:
            entity_matches = self._search_entities(company_name)
            results['matches'].extend(entity_matches)
            results['offshore_hits'] += len(entity_matches)

        # Search officers if provided
        if officers and self.officers_df is not None:
            for officer in officers:
                officer_matches = self._search_officers(officer)
                for match in officer_matches:
                    match['searched_officer'] = officer
                results['matches'].extend(officer_matches)
                results['offshore_hits'] += len(officer_matches)

        # Extract jurisdictions
        jurisdictions = set()
        for match in results['matches']:
            jurisdiction = match.get('jurisdiction', '')
            if jurisdiction:
                jurisdictions.add(jurisdiction)

        results['jurisdictions'] = list(jurisdictions)

        # Generate red flags
        if results['offshore_hits'] > 0:
            results['red_flags'].append(f'Found in {results["offshore_hits"]} offshore leak(s)')

        for jurisdiction in jurisdictions:
            if is_tax_haven(jurisdiction):
                results['red_flags'].append(f'Tax haven jurisdiction: {jurisdiction}')

        # Check for dissolved/inactive entities
        for match in results['matches']:
            if match.get('inactivation_date') or match.get('struck_off_date'):
                results['red_flags'].append(f"Entity {match['name']} was dissolved/struck off")

        return results

    def _search_entities(self, company_name: str) -> List[Dict[str, Any]]:
        """
        Search for company in entities database.

        Args:
            company_name: Company name

        Returns:
            List of matching entities
        """
        if self.entities_df is None:
            return []

        matches = []
        normalized_search = normalize_company_name(company_name)

        # Search in both name and original_name columns
        name_matches = self.entities_df[
            self.entities_df['name'].fillna('').str.upper().str.contains(normalized_search, regex=False, na=False)
        ]

        for _, entity in name_matches.head(10).iterrows():
            matches.append({
                'node_id': entity.get('node_id', ''),
                'name': entity.get('name', ''),
                'original_name': entity.get('original_name', ''),
                'jurisdiction': entity.get('jurisdiction_description', '') or entity.get('jurisdiction', ''),
                'source_investigation': entity.get('sourceID', ''),
                'incorporation_date': entity.get('incorporation_date', ''),
                'inactivation_date': entity.get('inactivation_date', ''),
                'struck_off_date': entity.get('struck_off_date', ''),
                'closed_date': entity.get('closed_date', ''),
                'service_provider': entity.get('service_provider', ''),
                'countries': entity.get('countries', ''),
                'entity_type': 'offshore_entity'
            })

        return matches

    def _search_officers(self, officer_name: str) -> List[Dict[str, Any]]:
        """
        Search for officer in officers database.

        Args:
            officer_name: Officer name

        Returns:
            List of matching officers
        """
        if self.officers_df is None:
            return []

        matches = []
        normalized_search = normalize_company_name(officer_name)

        name_matches = self.officers_df[
            self.officers_df['name'].fillna('').str.upper().str.contains(normalized_search, regex=False, na=False)
        ]

        for _, officer in name_matches.head(5).iterrows():
            matches.append({
                'node_id': officer.get('node_id', ''),
                'name': officer.get('name', ''),
                'countries': officer.get('countries', ''),
                'source_investigation': officer.get('sourceID', ''),
                'entity_type': 'offshore_officer'
            })

        return matches

    def get_related_entities(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Get entities related to a given node.

        Args:
            node_id: Node ID from ICIJ database

        Returns:
            List of related entities
        """
        if not self.data_loaded or self.relationships_df is None:
            return []

        # Find all relationships involving this node
        relationships = self.relationships_df[
            (self.relationships_df['node_1'] == node_id) |
            (self.relationships_df['node_2'] == node_id)
        ]

        related = []
        for _, rel in relationships.head(20).iterrows():
            related.append({
                'relationship_type': rel.get('rel_type', ''),
                'node_1': rel.get('node_1', ''),
                'node_2': rel.get('node_2', ''),
                'source': rel.get('sourceID', ''),
                'start_date': rel.get('start_date', ''),
                'end_date': rel.get('end_date', '')
            })

        return related
