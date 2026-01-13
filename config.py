"""Configuration settings for the Company Research Tool."""

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# API Keys
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
OPENCORPORATES_API_TOKEN = os.getenv("OPENCORPORATES_API_TOKEN", "")

# Rate limiting
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "2"))

# API URLs
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
OPENCORPORATES_URL = "https://api.opencorporates.com/v0.4"

# High-risk jurisdictions for shell company detection
HIGH_RISK_JURISDICTIONS = ["ky", "vg", "pa", "bz", "sc", "ae", "hk"]
MEDIUM_RISK_JURISDICTIONS = ["us_de", "gb", "sg"]

# Scoring weights (sum to 1.0)
SCORING_WEIGHTS = {
    "online_activity": 0.30,
    "corporate_info": 0.25,
    "officers_structure": 0.20,
    "jurisdiction_risk": 0.15,
    "external_factors": 0.10,
}


def validate_config() -> tuple[bool, list[str]]:
    """Validate configuration settings.
    
    Returns:
        Tuple of (is_valid, list of errors)
    """
    errors = []
    
    # Validate scoring weights sum to 1.0
    weight_sum = sum(SCORING_WEIGHTS.values())
    if not 0.99 <= weight_sum <= 1.01:
        errors.append(
            f"Scoring weights sum to {weight_sum:.2f}, expected 1.0. "
            "Please adjust SCORING_WEIGHTS in config.py"
        )
    
    # Validate rate delay is positive
    if RATE_LIMIT_DELAY <= 0:
        errors.append(f"RATE_LIMIT_DELAY must be positive, got {RATE_LIMIT_DELAY}")
    
    # Validate jurisdictions are lowercase
    for jur in HIGH_RISK_JURISDICTIONS + MEDIUM_RISK_JURISDICTIONS:
        if jur != jur.lower():
            errors.append(f"Jurisdiction '{jur}' should be lowercase")
    
    # Check for overlapping jurisdictions
    overlap = set(HIGH_RISK_JURISDICTIONS) & set(MEDIUM_RISK_JURISDICTIONS)
    if overlap:
        errors.append(
            f"Jurisdictions appear in both HIGH and MEDIUM risk lists: {overlap}"
        )
    
    return len(errors) == 0, errors


def get_config_summary() -> dict[str, Any]:
    """Get configuration summary for display.
    
    Returns:
        Dict with configuration info
    """
    is_valid, errors = validate_config()
    return {
        "brave_api_configured": bool(BRAVE_API_KEY),
        "opencorporates_configured": bool(OPENCORPORATES_API_TOKEN),
        "rate_limit_delay": RATE_LIMIT_DELAY,
        "scoring_weight_sum": sum(SCORING_WEIGHTS.values()),
        "high_risk_jurisdictions": len(HIGH_RISK_JURISDICTIONS),
        "medium_risk_jurisdictions": len(MEDIUM_RISK_JURISDICTIONS),
        "config_valid": is_valid,
        "config_errors": errors,
    }
