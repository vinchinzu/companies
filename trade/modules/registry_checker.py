"""
Registry verification module.
Checks company registration status with UK Companies House and US SEC EDGAR.
"""

from typing import Dict, Any, Optional, List
from utils.api_client import APIClient
from utils.helpers import normalize_company_name, parse_date, days_since, is_recent, format_cik
from config import Config


class RegistryChecker:
    """Check company registration with official registries."""

    def __init__(self):
        """Initialize registry clients."""
        self.companies_house_client = None
        self.sec_client = None

        if Config.is_configured('companies_house'):
            self.companies_house_client = APIClient(
                Config.COMPANIES_HOUSE_BASE_URL,
                rate_limit=Config.COMPANIES_HOUSE_RATE_LIMIT
            )

        # SEC EDGAR doesn't require API key
        self.sec_client = APIClient(
            Config.SEC_EDGAR_BASE_URL,
            rate_limit=Config.SEC_EDGAR_RATE_LIMIT
        )

    def check(self, company_name: str, country: str = 'US') -> Dict[str, Any]:
        """
        Check company registration.

        Args:
            company_name: Company name to check
            country: Country code (US, GB)

        Returns:
            Registry check results
        """
        if country.upper() == 'GB':
            return self._check_uk(company_name)
        elif country.upper() == 'US':
            return self._check_us(company_name)
        else:
            return {
                'found': False,
                'status': 'not_supported',
                'jurisdiction': country,
                'error': f'Registry checking not supported for country: {country}',
                'red_flags': ['Jurisdiction not supported'],
                'confidence': 0.0
            }

    def _check_uk(self, company_name: str) -> Dict[str, Any]:
        """
        Check UK Companies House.

        Args:
            company_name: Company name

        Returns:
            Registry results
        """
        if not self.companies_house_client:
            return {
                'found': False,
                'status': 'not_configured',
                'jurisdiction': 'GB',
                'error': 'Companies House API key not configured',
                'red_flags': ['API not configured'],
                'confidence': 0.0
            }

        # Search for company
        search_results = self.companies_house_client.get(
            '/search/companies',
            params={'q': company_name, 'items_per_page': 5},
            auth=(Config.COMPANIES_HOUSE_API_KEY, '')
        )

        if not search_results or 'items' not in search_results or not search_results['items']:
            return {
                'found': False,
                'status': 'not_found',
                'jurisdiction': 'GB',
                'red_flags': ['Company not found in UK registry'],
                'confidence': 1.0
            }

        # Get the best match (first result)
        company = search_results['items'][0]
        company_number = company['company_number']

        # Get detailed company profile
        profile = self.companies_house_client.get(
            f'/company/{company_number}',
            auth=(Config.COMPANIES_HOUSE_API_KEY, '')
        )

        if not profile:
            return {
                'found': True,
                'status': 'error',
                'jurisdiction': 'GB',
                'company_number': company_number,
                'error': 'Failed to fetch company profile',
                'red_flags': [],
                'confidence': 0.5
            }

        # Get filing history
        filings = self.companies_house_client.get(
            f'/company/{company_number}/filing-history',
            params={'items_per_page': 10},
            auth=(Config.COMPANIES_HOUSE_API_KEY, '')
        )

        # Get officers
        officers = self.companies_house_client.get(
            f'/company/{company_number}/officers',
            params={'items_per_page': 10},
            auth=(Config.COMPANIES_HOUSE_API_KEY, '')
        )

        # Analyze results
        red_flags = []
        status = profile.get('company_status', 'unknown')

        if status != 'active':
            red_flags.append(f'Company status: {status}')

        # Check incorporation date
        incorporation_date = profile.get('date_of_creation')
        if incorporation_date and days_since(incorporation_date) is not None:
            age_days = days_since(incorporation_date)
            if age_days < 365:
                red_flags.append(f'Recently incorporated ({age_days} days ago)')

        # Check accounts
        accounts = profile.get('accounts', {})
        last_accounts = accounts.get('last_accounts', {}).get('made_up_to')
        if last_accounts and not is_recent(last_accounts, days=365):
            red_flags.append('No recent accounts filed (over 1 year)')

        # Check confirmation statement
        confirmation = profile.get('confirmation_statement', {})
        last_confirmation = confirmation.get('last_made_up_to')
        if last_confirmation and not is_recent(last_confirmation, days=365):
            red_flags.append('No recent confirmation statement')

        # Check officers
        officers_count = 0
        if officers and 'items' in officers:
            officers_count = len(officers['items'])
            if officers_count == 0:
                red_flags.append('No officers listed')

        # Check filing activity
        recent_filings = 0
        if filings and 'items' in filings:
            for filing in filings['items']:
                filing_date = filing.get('date')
                if filing_date and is_recent(filing_date, days=180):
                    recent_filings += 1

        if recent_filings == 0:
            red_flags.append('No filings in last 6 months')

        return {
            'found': True,
            'status': status,
            'jurisdiction': 'GB',
            'company_number': company_number,
            'company_name': profile.get('company_name'),
            'incorporation_date': incorporation_date,
            'company_type': profile.get('type'),
            'last_accounts_date': last_accounts,
            'last_confirmation_date': last_confirmation,
            'officers_count': officers_count,
            'recent_filings': recent_filings,
            'address': profile.get('registered_office_address', {}),
            'sic_codes': profile.get('sic_codes', []),
            'has_insolvency_history': profile.get('has_insolvency_history', False),
            'has_charges': profile.get('has_charges', False),
            'red_flags': red_flags,
            'confidence': 1.0
        }

    def _check_us(self, company_name: str) -> Dict[str, Any]:
        """
        Check US SEC EDGAR.

        Args:
            company_name: Company name

        Returns:
            Registry results
        """
        # SEC EDGAR requires User-Agent header
        headers = {
            'User-Agent': Config.USER_AGENT
        }

        # Search for company in company tickers JSON
        # This is a publicly available file
        tickers_url = 'https://www.sec.gov/files/company_tickers.json'

        try:
            import requests
            response = requests.get(tickers_url, headers=headers, timeout=Config.API_TIMEOUT)
            response.raise_for_status()
            tickers_data = response.json()
        except Exception as e:
            return {
                'found': False,
                'status': 'error',
                'jurisdiction': 'US',
                'error': f'Failed to search SEC EDGAR: {str(e)}',
                'red_flags': [],
                'confidence': 0.0
            }

        # Search for company
        normalized_search = normalize_company_name(company_name)
        matches = []

        for key, company in tickers_data.items():
            company_title = company.get('title', '')
            if normalized_search in normalize_company_name(company_title):
                matches.append(company)

        if not matches:
            return {
                'found': False,
                'status': 'not_found',
                'jurisdiction': 'US',
                'red_flags': ['Company not found in SEC EDGAR'],
                'confidence': 1.0
            }

        # Get best match
        best_match = matches[0]
        cik = format_cik(best_match['cik_str'])

        # Get company submissions
        submissions = self.sec_client.get(
            f'/submissions/CIK{cik}.json',
            headers=headers
        )

        if not submissions:
            return {
                'found': True,
                'status': 'error',
                'jurisdiction': 'US',
                'cik': cik,
                'error': 'Failed to fetch company submissions',
                'red_flags': [],
                'confidence': 0.5
            }

        # Analyze filings
        red_flags = []
        recent_filings = submissions.get('filings', {}).get('recent', {})

        if not recent_filings or 'form' not in recent_filings:
            red_flags.append('No recent filings found')
            recent_10k = None
            recent_10q = None
        else:
            # Count recent filings (last 6 months)
            filing_dates = recent_filings.get('filingDate', [])
            forms = recent_filings.get('form', [])

            recent_count = 0
            recent_10k = None
            recent_10q = None

            for i, filing_date in enumerate(filing_dates):
                if is_recent(filing_date, days=180):
                    recent_count += 1

                    form = forms[i] if i < len(forms) else ''
                    if form == '10-K' and not recent_10k:
                        recent_10k = filing_date
                    elif form == '10-Q' and not recent_10q:
                        recent_10q = filing_date

            if recent_count == 0:
                red_flags.append('No SEC filings in last 6 months')

            if not recent_10k and not recent_10q:
                red_flags.append('No recent 10-K or 10-Q filings')

        # Check entity type
        entity_type = submissions.get('entityType')
        if entity_type and 'shell' in entity_type.lower():
            red_flags.append('SEC labels entity type as shell company')

        return {
            'found': True,
            'status': 'active',
            'jurisdiction': 'US',
            'cik': cik,
            'company_name': submissions.get('name'),
            'tickers': submissions.get('tickers', []),
            'exchanges': submissions.get('exchanges', []),
            'sic': submissions.get('sic'),
            'sic_description': submissions.get('sicDescription'),
            'entity_type': entity_type,
            'fiscal_year_end': submissions.get('fiscalYearEnd'),
            'recent_10k_date': recent_10k,
            'recent_10q_date': recent_10q,
            'red_flags': red_flags,
            'confidence': 1.0
        }

    def close(self):
        """Close API clients."""
        if self.companies_house_client:
            self.companies_house_client.close()
        if self.sec_client:
            self.sec_client.close()
