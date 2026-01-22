"""
Helper functions for data processing and normalization.
"""

import re
from datetime import datetime, timedelta
from typing import Optional


def normalize_company_name(name: str) -> str:
    """
    Normalize company name for better matching.

    Args:
        name: Company name

    Returns:
        Normalized company name
    """
    # Convert to uppercase
    normalized = name.upper()

    # Remove common suffixes
    suffixes = [
        r'\s+LTD\.?$',
        r'\s+LIMITED$',
        r'\s+INC\.?$',
        r'\s+INCORPORATED$',
        r'\s+CORP\.?$',
        r'\s+CORPORATION$',
        r'\s+LLC$',
        r'\s+L\.L\.C\.$',
        r'\s+PLC$',
        r'\s+P\.L\.C\.$',
        r'\s+CO\.?$',
        r'\s+COMPANY$',
    ]

    for suffix in suffixes:
        normalized = re.sub(suffix, '', normalized)

    # Remove extra whitespace
    normalized = ' '.join(normalized.split())

    return normalized


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse date string to datetime object.

    Args:
        date_str: Date string in various formats

    Returns:
        datetime object or None
    """
    if not date_str:
        return None

    # Common date formats
    formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%SZ',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def days_since(date_str: Optional[str]) -> Optional[int]:
    """
    Calculate days since a given date.

    Args:
        date_str: Date string

    Returns:
        Number of days or None
    """
    parsed_date = parse_date(date_str)
    if parsed_date:
        return (datetime.now() - parsed_date).days
    return None


def is_recent(date_str: Optional[str], days: int = 180) -> bool:
    """
    Check if date is within the last N days.

    Args:
        date_str: Date string
        days: Number of days to consider recent

    Returns:
        True if recent, False otherwise
    """
    days_ago = days_since(date_str)
    return days_ago is not None and days_ago <= days


def is_tax_haven(jurisdiction: str) -> bool:
    """
    Check if jurisdiction is a known tax haven.

    Args:
        jurisdiction: Country or jurisdiction code

    Returns:
        True if tax haven, False otherwise
    """
    tax_havens = {
        'BVI', 'BRITISH VIRGIN ISLANDS',
        'PANAMA',
        'CAYMAN ISLANDS', 'CAYMAN',
        'BAHAMAS',
        'BERMUDA',
        'SEYCHELLES',
        'GIBRALTAR',
        'JERSEY',
        'GUERNSEY',
        'ISLE OF MAN',
        'LUXEMBOURG',
        'MALTA',
        'CYPRUS',
        'BELIZE',
        'SAMOA',
        'MAURITIUS',
        'LIECHTENSTEIN',
        'MONACO',
        'HONG KONG',
        'SINGAPORE',
        'SWITZERLAND',
        'DELAWARE', 'DE',  # US state known for incorporation
        'NEVADA', 'NV',
    }

    return jurisdiction.upper() in tax_havens


def format_currency(value: float) -> str:
    """
    Format number as currency.

    Args:
        value: Numeric value

    Returns:
        Formatted string
    """
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.2f}K"
    else:
        return f"${value:.2f}"


def calculate_confidence(checks_performed: int, checks_successful: int) -> float:
    """
    Calculate confidence score based on successful checks.

    Args:
        checks_performed: Total number of checks attempted
        checks_successful: Number of checks that returned data

    Returns:
        Confidence score (0.0 to 1.0)
    """
    if checks_performed == 0:
        return 0.0

    return min(1.0, checks_successful / checks_performed)


def format_cik(cik: str) -> str:
    """
    Format CIK (Central Index Key) to 10 digits with leading zeros.

    Args:
        cik: CIK string or number

    Returns:
        10-digit CIK string
    """
    cik_str = str(cik).strip()
    # Remove non-digits
    cik_str = re.sub(r'\D', '', cik_str)
    # Pad to 10 digits
    return cik_str.zfill(10)
