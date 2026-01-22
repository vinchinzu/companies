"""
Trade activity checker module.
Verifies business operations through trade data (UN Comtrade).
"""

from typing import Dict, Any, Optional
from utils.api_client import APIClient
from config import Config


class TradeChecker:
    """Check trade activity to verify real business operations."""

    def __init__(self):
        """Initialize trade checker."""
        self.comtrade_client = None

        if Config.is_configured('comtrade'):
            # UN Comtrade API (v1)
            self.comtrade_client = APIClient('https://comtradeapi.un.org')

    def check(
        self,
        company_name: str,
        country_code: str = 'US',
        industry_hs_code: Optional[str] = None,
        business_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check trade activity for company's country and industry.

        Note: UN Comtrade only provides country-level aggregate data,
        not company-specific shipments. This method infers whether
        the country has trade activity in the claimed industry.

        Args:
            company_name: Company name (for ImportYeti URL generation)
            country_code: ISO country code
            industry_hs_code: HS code for industry (e.g., '85' for electronics)
            business_description: Company's business description

        Returns:
            Trade activity results
        """
        results = {
            'has_trade_data': False,
            'country_trade_volume': 0.0,
            'industry_aligned': False,
            'manual_check_needed': True,
            'importyeti_url': f'https://www.importyeti.com/search?q={company_name.replace(" ", "+")}',
            'red_flags': [],
            'confidence': 0.5,
            'note': 'UN Comtrade provides country-level data only. Use ImportYeti for company-specific verification.'
        }

        # If no Comtrade API configured, return guidance for manual check
        if not self.comtrade_client:
            results['red_flags'].append('UN Comtrade API not configured')
            results['note'] = 'Manual verification recommended via ImportYeti for US companies'
            return results

        # If no industry code provided, cannot check trade alignment
        if not industry_hs_code:
            results['red_flags'].append('No industry HS code provided for trade verification')
            results['note'] = 'Provide HS code (e.g., 85 for electronics) to check trade patterns'
            return results

        # Query UN Comtrade for country's trade in specified industry
        # This is aggregate data, not company-specific
        trade_data = self._query_comtrade(
            country_code=country_code,
            hs_code=industry_hs_code
        )

        if trade_data:
            results['has_trade_data'] = True
            results['country_trade_volume'] = trade_data.get('total_value', 0.0)
            results['industry_aligned'] = trade_data.get('total_value', 0.0) > 0
            results['confidence'] = 0.7

            if trade_data.get('total_value', 0.0) == 0:
                results['red_flags'].append(
                    f'Country {country_code} has zero/minimal trade in HS code {industry_hs_code}'
                )
        else:
            results['red_flags'].append('Failed to retrieve Comtrade data')

        return results

    def _query_comtrade(
        self,
        country_code: str,
        hs_code: str,
        year: str = '2023',
        flow: str = 'X'  # X = exports, M = imports
    ) -> Optional[Dict[str, Any]]:
        """
        Query UN Comtrade API for aggregate trade data.

        Args:
            country_code: ISO country code (will convert to M49 code)
            hs_code: HS product code
            year: Year for data (YYYY)
            flow: Trade flow (X=export, M=import)

        Returns:
            Trade data summary or None
        """
        if not Config.UN_COMTRADE_SUBSCRIPTION_KEY:
            return None

        # Country code mapping (ISO2 to M49)
        # This is a simplified mapping - full implementation would use complete lookup table
        country_m49_map = {
            'US': '842',  # United States
            'GB': '826',  # United Kingdom
            'CN': '156',  # China
            'DE': '276',  # Germany
            'FR': '250',  # France
            'JP': '392',  # Japan
            'IN': '356',  # India
            'BR': '076',  # Brazil
            'RU': '643',  # Russia
            'IR': '364',  # Iran
            'VE': '862',  # Venezuela
            'KP': '408',  # North Korea
            'WS': '882',  # Samoa
        }

        reporter_code = country_m49_map.get(country_code.upper())
        if not reporter_code:
            print(f"Warning: Country code {country_code} not in mapping. Using code directly.")
            reporter_code = country_code

        # Build request parameters (v1 endpoint)
        params = {
            'period': year,
            'reporterCode': reporter_code,
            'cmdCode': hs_code,
            'flowCode': flow,
            'partnerCode': '0',  # World (all partners)
            'partner2Code': '0',
            'customsCode': 'C00',
            'motCode': '0',
            'includeDesc': 'TRUE',
            'maxRecords': 100,
            'subscription-key': Config.UN_COMTRADE_SUBSCRIPTION_KEY,
        }

        try:
            # v1 endpoint: /data/v1/get/C/A/HS
            response = self.comtrade_client.get(
                '/data/v1/get/C/A/HS',
                params=params
            )

            if response and 'data' in response:
                # Aggregate total trade value
                total_value = 0.0
                for record in response['data']:
                    value = record.get('primaryValue', 0) or record.get('fobvalue', 0) or 0
                    total_value += float(value)

                return {
                    'total_value': total_value,
                    'records_count': len(response['data']),
                    'year': year,
                    'flow': flow,
                    'hs_code': hs_code
                }

            return None

        except Exception as e:
            print(f"Error querying Comtrade: {e}")
            return None

    def get_importyeti_info(self, company_name: str) -> Dict[str, str]:
        """
        Generate ImportYeti URLs for manual verification.

        Args:
            company_name: Company name

        Returns:
            Dictionary with ImportYeti links
        """
        formatted_name = company_name.replace(' ', '+')

        return {
            'search_url': f'https://www.importyeti.com/search?q={formatted_name}',
            'note': 'ImportYeti provides free US Bill of Lading data. Check manually for company-level trade.',
            'instructions': [
                '1. Visit the search URL',
                '2. Look for shipment records',
                '3. Verify if company has actual import/export activity',
                '4. Check supplier/buyer relationships',
                '5. Look for recent shipments (last 6-12 months)'
            ]
        }

    def close(self):
        """Close API clients."""
        if self.comtrade_client:
            self.comtrade_client.close()
