"""
Sanctions screening module.
Checks against OpenSanctions and ITA Consolidated Screening List.
"""

from typing import Dict, Any, List
from utils.api_client import APIClient
from utils.helpers import normalize_company_name
from config import Config


class SanctionsChecker:
    """Screen companies against sanctions lists and PEP databases."""

    def __init__(self):
        """Initialize sanctions screening clients."""
        self.opensanctions_client = None
        self.ita_client = None

        if Config.is_configured('opensanctions'):
            self.opensanctions_client = APIClient(Config.OPENSANCTIONS_BASE_URL)

        if Config.is_configured('ita'):
            self.ita_client = APIClient(Config.ITA_BASE_URL)

    def check(self, company_name: str, officers: List[str] = None) -> Dict[str, Any]:
        """
        Screen company and officers against sanctions lists.

        Args:
            company_name: Company name to screen
            officers: List of officer names to screen

        Returns:
            Sanctions screening results
        """
        results = {
            'sanctions_hits': 0,
            'pep_hits': 0,
            'matches': [],
            'red_flags': [],
            'confidence': 0.0,
            'sources_checked': []
        }

        checks_performed = 0
        checks_successful = 0

        # Check OpenSanctions
        if self.opensanctions_client:
            checks_performed += 1
            os_result = self._check_opensanctions(company_name, officers)
            if os_result:
                checks_successful += 1
                results['matches'].extend(os_result['matches'])
                results['sanctions_hits'] += os_result['sanctions_hits']
                results['pep_hits'] += os_result['pep_hits']
                results['sources_checked'].append('OpenSanctions')

        # Check ITA Consolidated Screening List
        if self.ita_client:
            checks_performed += 1
            ita_result = self._check_ita(company_name, officers)
            if ita_result:
                checks_successful += 1
                results['matches'].extend(ita_result['matches'])
                results['sanctions_hits'] += ita_result['sanctions_hits']
                results['sources_checked'].append('ITA CSL')

        # Generate red flags
        if results['sanctions_hits'] > 0:
            results['red_flags'].append(f'Found {results["sanctions_hits"]} sanctions match(es)')

        if results['pep_hits'] > 0:
            results['red_flags'].append(f'Found {results["pep_hits"]} PEP match(es)')

        # Calculate confidence
        if checks_performed > 0:
            results['confidence'] = checks_successful / checks_performed
        else:
            results['red_flags'].append('No sanctions APIs configured')

        return results

    def _check_opensanctions(self, company_name: str, officers: List[str] = None) -> Dict[str, Any]:
        """
        Check OpenSanctions API.

        Args:
            company_name: Company name
            officers: List of officer names

        Returns:
            OpenSanctions results
        """
        if not Config.OPENSANCTIONS_API_KEY:
            print("Warning: OpenSanctions API key not configured")
            return None

        headers = {
            'Authorization': f'ApiKey {Config.OPENSANCTIONS_API_KEY}'
        }

        results = {
            'sanctions_hits': 0,
            'pep_hits': 0,
            'matches': []
        }

        # Search for company
        response = self.opensanctions_client.get(
            '/search/default',
            params={
                'q': company_name,
                'schema': 'Company',
                'limit': 5
            },
            headers=headers
        )

        if response and 'results' in response:
            for entity in response['results']:
                match_type = self._classify_opensanctions_entity(entity)

                results['matches'].append({
                    'name': entity.get('caption', ''),
                    'type': match_type,
                    'source': 'OpenSanctions',
                    'datasets': entity.get('datasets', []),
                    'schema': entity.get('schema'),
                    'countries': entity.get('properties', {}).get('country', []),
                    'confidence': entity.get('score', 0.0)
                })

                if match_type == 'sanctions':
                    results['sanctions_hits'] += 1
                elif match_type == 'pep':
                    results['pep_hits'] += 1

        # Screen officers if provided
        if officers:
            for officer in officers:
                officer_response = self.opensanctions_client.get(
                    '/search/default',
                    params={
                        'q': officer,
                        'schema': 'Person',
                        'limit': 3
                    },
                    headers=headers
                )

                if officer_response and 'results' in officer_response:
                    for entity in officer_response['results']:
                        match_type = self._classify_opensanctions_entity(entity)

                        results['matches'].append({
                            'name': entity.get('caption', ''),
                            'officer_name': officer,
                            'type': match_type,
                            'source': 'OpenSanctions',
                            'datasets': entity.get('datasets', []),
                            'schema': entity.get('schema'),
                            'confidence': entity.get('score', 0.0)
                        })

                        if match_type == 'sanctions':
                            results['sanctions_hits'] += 1
                        elif match_type == 'pep':
                            results['pep_hits'] += 1

        return results

    def _classify_opensanctions_entity(self, entity: Dict) -> str:
        """
        Classify OpenSanctions entity as sanctions or PEP.

        Args:
            entity: Entity from OpenSanctions

        Returns:
            'sanctions', 'pep', or 'other'
        """
        datasets = entity.get('datasets', [])
        topics = entity.get('properties', {}).get('topics', [])

        # Check for sanctions indicators
        sanctions_keywords = ['sanctions', 'sdn', 'ofac', 'dpl', 'entity_list']
        for keyword in sanctions_keywords:
            for dataset in datasets:
                if keyword in dataset.lower():
                    return 'sanctions'

        # Check for PEP indicators
        pep_keywords = ['pep', 'politically_exposed']
        for keyword in pep_keywords:
            for dataset in datasets:
                if keyword in dataset.lower():
                    return 'pep'
            for topic in topics:
                if keyword in topic.lower():
                    return 'pep'

        return 'other'

    def _check_ita(self, company_name: str, officers: List[str] = None) -> Dict[str, Any]:
        """
        Check ITA Consolidated Screening List.

        Args:
            company_name: Company name
            officers: List of officer names

        Returns:
            ITA CSL results
        """
        if not Config.ITA_SUBSCRIPTION_KEY:
            print("Warning: ITA API key not configured")
            return None

        headers = {
            'subscription-key': Config.ITA_SUBSCRIPTION_KEY
        }

        results = {
            'sanctions_hits': 0,
            'matches': []
        }

        # Search screening list
        response = self.ita_client.get(
            '/consolidated_screening_list/v1/search',
            params={
                'name': company_name,
                'fuzzy_name': 'true',
                'size': 10
            },
            headers=headers
        )

        if response and 'results' in response:
            for hit in response['results']:
                results['matches'].append({
                    'name': hit.get('name', ''),
                    'type': 'sanctions',
                    'source': f"ITA CSL - {hit.get('source', '')}",
                    'programs': hit.get('programs', []),
                    'addresses': hit.get('addresses', []),
                    'remarks': hit.get('remarks', ''),
                    'source_list_url': hit.get('source_list_url', '')
                })

                results['sanctions_hits'] += 1

        # Screen officers if provided
        if officers:
            for officer in officers:
                officer_response = self.ita_client.get(
                    '/consolidated_screening_list/v1/search',
                    params={
                        'name': officer,
                        'fuzzy_name': 'true',
                        'size': 5
                    },
                    headers=headers
                )

                if officer_response and 'results' in officer_response:
                    for hit in officer_response['results']:
                        results['matches'].append({
                            'name': hit.get('name', ''),
                            'officer_name': officer,
                            'type': 'sanctions',
                            'source': f"ITA CSL - {hit.get('source', '')}",
                            'programs': hit.get('programs', []),
                            'remarks': hit.get('remarks', '')
                        })

                        results['sanctions_hits'] += 1

        return results

    def close(self):
        """Close API clients."""
        if self.opensanctions_client:
            self.opensanctions_client.close()
        if self.ita_client:
            self.ita_client.close()
