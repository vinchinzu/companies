"""
Configuration management for Company Verifier tool.
Loads API keys and settings from environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Central configuration for all API keys and settings."""

    # API Keys
    OPENSANCTIONS_API_KEY = os.getenv('OPENSANCTIONS_API_KEY', '')
    COMPANIES_HOUSE_API_KEY = os.getenv('COMPANIES_HOUSE_API_KEY', '')
    UN_COMTRADE_SUBSCRIPTION_KEY = os.getenv('UN_COMTRADE_SUBSCRIPTION_KEY', '')
    ITA_SUBSCRIPTION_KEY = os.getenv('PRIMARY_KEY', '') or os.getenv('ITA_SUBSCRIPTION_KEY', '')

    # Data paths
    ICIJ_DATA_PATH = os.getenv('ICIJ_DATA_PATH', './data/icij_offshore')

    # User agent for SEC EDGAR (required)
    USER_AGENT = os.getenv('USER_AGENT', 'CompanyVerifier/1.0 (research@example.com)')

    # API Base URLs
    OPENSANCTIONS_BASE_URL = 'https://api.opensanctions.org'
    COMPANIES_HOUSE_BASE_URL = 'https://api.companieshouse.gov.uk'
    SEC_EDGAR_BASE_URL = 'https://data.sec.gov'
    ITA_BASE_URL = 'https://data.trade.gov'  # Fixed: was api.trade.gov

    # Rate limiting settings (requests per second)
    COMPANIES_HOUSE_RATE_LIMIT = 2  # 600 per 5 min = 2/sec safe
    SEC_EDGAR_RATE_LIMIT = 7  # 10/sec limit, use 7 for safety

    # Timeout settings (seconds)
    API_TIMEOUT = 30

    # Retry settings
    MAX_RETRIES = 3
    RETRY_BACKOFF = 2  # Exponential backoff factor

    # Scoring weights
    REGISTRY_WEIGHT = 25
    SANCTIONS_WEIGHT = 50
    OFFSHORE_WEIGHT = 20
    TRADE_WEIGHT = 15

    @classmethod
    def validate(cls):
        """
        Validate that required API keys are configured.
        Returns list of missing keys.
        """
        missing = []

        if not cls.OPENSANCTIONS_API_KEY:
            missing.append('OPENSANCTIONS_API_KEY (optional but recommended)')

        if not cls.COMPANIES_HOUSE_API_KEY:
            missing.append('COMPANIES_HOUSE_API_KEY (required for UK companies)')

        if not cls.ITA_SUBSCRIPTION_KEY:
            missing.append('ITA_SUBSCRIPTION_KEY (optional for sanctions screening)')

        return missing

    @classmethod
    def is_configured(cls, service):
        """Check if a specific service is configured."""
        service_keys = {
            'opensanctions': cls.OPENSANCTIONS_API_KEY,
            'companies_house': cls.COMPANIES_HOUSE_API_KEY,
            'comtrade': cls.UN_COMTRADE_SUBSCRIPTION_KEY,
            'ita': cls.ITA_SUBSCRIPTION_KEY
        }
        return bool(service_keys.get(service.lower(), False))
