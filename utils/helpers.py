"""Common utility functions."""

import time
from datetime import datetime
from functools import wraps
from typing import Any, Optional


def rate_limit(delay: float):
    """Decorator to add delay between function calls for rate limiting."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            time.sleep(delay)
            return result
        return wrapper
    return decorator


def safe_get(data: dict, *keys, default: Any = None) -> Any:
    """Safely get nested dictionary values."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data


def parse_date(date_string: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime object."""
    if not date_string:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue

    return None


def calculate_lifespan_days(incorporation_date: Optional[str]) -> Optional[int]:
    """Calculate company lifespan in days from incorporation date."""
    if not incorporation_date:
        return None

    inc_date = parse_date(incorporation_date)
    if not inc_date:
        try:
            inc_date = datetime.fromisoformat(incorporation_date.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    return (datetime.now() - inc_date).days


def normalize_jurisdiction(jurisdiction: str) -> str:
    """Normalize jurisdiction codes to lowercase."""
    if not jurisdiction:
        return ""
    return jurisdiction.lower().strip()


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    if not url:
        return ""

    url = url.lower()
    url = url.replace("https://", "").replace("http://", "")
    url = url.replace("www.", "")

    return url.split("/")[0]
