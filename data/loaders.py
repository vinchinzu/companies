"""Cached data loaders for the Company Research Tool.

Provides cached versions of data loading functions to avoid
reloading expensive datasets on every page refresh.
"""

import os
from typing import Optional

import pandas as pd
import streamlit as st


@st.cache_data(ttl=3600, show_spinner=False)
def load_fraud_dataset() -> Optional[pd.DataFrame]:
    """Load the fraud dataset if available.
    
    Cached with 1-hour TTL to avoid repeated file I/O.
    
    Returns:
        DataFrame with fraud cases or None if not found
    """
    dataset_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "fraudulent_companies.csv"
    )
    if os.path.exists(dataset_path):
        try:
            return pd.read_csv(dataset_path)
        except Exception:
            return None
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def load_ofac_names() -> set:
    """Load OFAC sanctioned names for screening.
    
    Cached with 1-hour TTL.
    
    Returns:
        Set of lowercase sanctioned names
    """
    names_file = os.path.join(
        os.path.dirname(__file__), "..", "data", "opensanctions", "us_ofac_press_releases.names.txt"
    )
    if os.path.exists(names_file):
        try:
            with open(names_file, 'r', encoding='utf-8') as f:
                return {line.strip().lower() for line in f if line.strip()}
        except Exception:
            return set()
    return set()


@st.cache_data(ttl=3600, show_spinner=False)
def load_consolidated_sanctions() -> set:
    """Load consolidated sanctions names.
    
    Returns:
        Set of lowercase sanctioned names
    """
    names_file = os.path.join(
        os.path.dirname(__file__), "..", "data", "opensanctions", "consolidated_names.txt"
    )
    if os.path.exists(names_file):
        try:
            with open(names_file, 'r', encoding='utf-8') as f:
                return {line.strip().lower() for line in f if line.strip()}
        except Exception:
            return set()
    return set()


@st.cache_data(ttl=3600, show_spinner=False)
def load_peps_names() -> set:
    """Load PEPs names.
    
    Returns:
        Set of lowercase PEP names
    """
    names_file = os.path.join(
        os.path.dirname(__file__), "..", "data", "opensanctions", "peps_names.txt"
    )
    if os.path.exists(names_file):
        try:
            with open(names_file, 'r', encoding='utf-8') as f:
                return {line.strip().lower() for line in f if line.strip()}
        except Exception:
            return set()
    return set()


def get_dataset_stats() -> dict:
    """Get statistics about loaded datasets.
    
    Returns:
        Dict with dataset info and counts
    """
    stats = {
        "fraud_cases": {"count": 0, "loaded": False},
        "ofac_names": {"count": 0, "loaded": False},
        "consolidated_sanctions": {"count": 0, "loaded": False},
        "peps": {"count": 0, "loaded": False},
    }
    
    fraud_df = load_fraud_dataset()
    if fraud_df is not None:
        stats["fraud_cases"]["count"] = len(fraud_df)
        stats["fraud_cases"]["loaded"] = True
    
    ofac = load_ofac_names()
    if ofac:
        stats["ofac_names"]["count"] = len(ofac)
        stats["ofac_names"]["loaded"] = True
    
    consolidated = load_consolidated_sanctions()
    if consolidated:
        stats["consolidated_sanctions"]["count"] = len(consolidated)
        stats["consolidated_sanctions"]["loaded"] = True
    
    peps = load_peps_names()
    if peps:
        stats["peps"]["count"] = len(peps)
        stats["peps"]["loaded"] = True
    
    return stats
