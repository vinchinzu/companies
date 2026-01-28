"""
Trade Verification UI - Stripe-level quality interface for company verification.

Features:
- Drag-and-drop file upload with visual feedback
- Smart column auto-detection
- Real-time processing with animated progress
- Beautiful results dashboard with risk visualization
- Multiple export formats (CSV, Excel, JSON)
"""

import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime
from io import BytesIO
from typing import Optional, Dict, Any, List, Tuple
import plotly.graph_objects as go
import plotly.express as px

# Import trade verification modules
import sys
from pathlib import Path

# Add trade module to path (append to avoid shadowing root utils/)
trade_path = Path(__file__).parent.parent / "trade"
if str(trade_path) not in sys.path:
    sys.path.append(str(trade_path))

try:
    from modules.registry_checker import RegistryChecker
    from modules.sanctions_checker import SanctionsChecker
    from modules.offshore_checker import OffshoreChecker
    from modules.trade_checker import TradeChecker
    from modules.risk_scorer import RiskScorer
    TRADE_MODULES_AVAILABLE = True
except ImportError:
    TRADE_MODULES_AVAILABLE = False


# ============================================================================
# CUSTOM CSS - Stripe-inspired design system
# ============================================================================

def inject_custom_css():
    """Inject Stripe-inspired CSS for premium UI/UX."""
    st.markdown("""
    <style>
    /* ===== DESIGN TOKENS ===== */
    :root {
        --stripe-purple: #635bff;
        --stripe-purple-light: #7a73ff;
        --stripe-purple-dark: #4f46e5;
        --stripe-green: #00d4aa;
        --stripe-green-light: #1aea9f;
        --stripe-yellow: #ffbb00;
        --stripe-red: #ff5252;
        --stripe-red-light: #ff7070;
        --stripe-blue: #00a1ff;

        --bg-primary: #0a0a0f;
        --bg-secondary: #12121a;
        --bg-tertiary: #1a1a24;
        --bg-card: linear-gradient(145deg, #16161f 0%, #1a1a26 100%);
        --bg-card-hover: linear-gradient(145deg, #1a1a26 0%, #1e1e2d 100%);

        --text-primary: #ffffff;
        --text-secondary: #a0a0b0;
        --text-muted: #6b6b7a;

        --border-subtle: rgba(255, 255, 255, 0.06);
        --border-light: rgba(255, 255, 255, 0.1);
        --border-accent: rgba(99, 91, 255, 0.3);

        --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
        --shadow-md: 0 4px 20px rgba(0, 0, 0, 0.4);
        --shadow-lg: 0 8px 40px rgba(0, 0, 0, 0.5);
        --shadow-glow: 0 0 40px rgba(99, 91, 255, 0.15);

        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --radius-xl: 24px;

        --transition-fast: 150ms ease;
        --transition-normal: 250ms ease;
        --transition-slow: 400ms ease;
    }

    /* ===== UPLOAD ZONE ===== */
    .upload-zone {
        background: var(--bg-card);
        border: 2px dashed var(--border-light);
        border-radius: var(--radius-xl);
        padding: 4rem 2rem;
        text-align: center;
        transition: all var(--transition-normal);
        position: relative;
        overflow: hidden;
    }

    .upload-zone::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: radial-gradient(ellipse at center, rgba(99, 91, 255, 0.05) 0%, transparent 70%);
        opacity: 0;
        transition: opacity var(--transition-normal);
    }

    .upload-zone:hover {
        border-color: var(--stripe-purple);
        box-shadow: var(--shadow-glow);
    }

    .upload-zone:hover::before {
        opacity: 1;
    }

    .upload-icon {
        font-size: 4rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(135deg, var(--stripe-purple) 0%, var(--stripe-blue) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .upload-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
    }

    .upload-subtitle {
        color: var(--text-secondary);
        font-size: 0.95rem;
    }

    .upload-formats {
        display: flex;
        justify-content: center;
        gap: 0.75rem;
        margin-top: 1.5rem;
    }

    .format-badge {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-sm);
        padding: 0.4rem 0.8rem;
        font-size: 0.8rem;
        color: var(--text-secondary);
        font-family: 'SF Mono', 'Fira Code', monospace;
    }

    /* ===== STEP INDICATOR ===== */
    .steps-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0;
        margin: 2rem 0 3rem;
        padding: 0 2rem;
    }

    .step {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        z-index: 1;
    }

    .step-circle {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 1rem;
        transition: all var(--transition-normal);
        position: relative;
    }

    .step-circle.inactive {
        background: var(--bg-tertiary);
        border: 2px solid var(--border-light);
        color: var(--text-muted);
    }

    .step-circle.active {
        background: linear-gradient(135deg, var(--stripe-purple) 0%, var(--stripe-purple-light) 100%);
        border: 2px solid var(--stripe-purple);
        color: white;
        box-shadow: 0 0 20px rgba(99, 91, 255, 0.4);
    }

    .step-circle.completed {
        background: linear-gradient(135deg, var(--stripe-green) 0%, var(--stripe-green-light) 100%);
        border: 2px solid var(--stripe-green);
        color: white;
    }

    .step-label {
        margin-top: 0.75rem;
        font-size: 0.85rem;
        font-weight: 500;
        transition: color var(--transition-fast);
    }

    .step-label.inactive { color: var(--text-muted); }
    .step-label.active { color: var(--stripe-purple-light); }
    .step-label.completed { color: var(--stripe-green); }

    .step-connector {
        width: 80px;
        height: 2px;
        background: var(--border-light);
        margin: 0 0.5rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }

    .step-connector.completed {
        background: var(--stripe-green);
    }

    .step-connector.active::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        height: 100%;
        width: 50%;
        background: linear-gradient(90deg, var(--stripe-purple), var(--stripe-green));
        animation: connector-progress 2s ease infinite;
    }

    @keyframes connector-progress {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(300%); }
    }

    /* ===== CARDS ===== */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        transition: all var(--transition-normal);
        position: relative;
        overflow: hidden;
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--stripe-purple), var(--stripe-blue));
        opacity: 0;
        transition: opacity var(--transition-normal);
    }

    .metric-card:hover {
        border-color: var(--border-accent);
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }

    .metric-card:hover::before {
        opacity: 1;
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--text-primary) 0%, var(--text-secondary) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.1;
    }

    .metric-label {
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin-top: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .metric-delta {
        font-size: 0.85rem;
        margin-top: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .metric-delta.positive { color: var(--stripe-green); }
    .metric-delta.negative { color: var(--stripe-red); }
    .metric-delta.neutral { color: var(--text-muted); }

    /* ===== RISK INDICATORS ===== */
    .risk-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: var(--radius-md);
        font-weight: 600;
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    .risk-badge.high {
        background: rgba(255, 82, 82, 0.15);
        border: 1px solid rgba(255, 82, 82, 0.3);
        color: var(--stripe-red-light);
    }

    .risk-badge.medium {
        background: rgba(255, 187, 0, 0.15);
        border: 1px solid rgba(255, 187, 0, 0.3);
        color: var(--stripe-yellow);
    }

    .risk-badge.low {
        background: rgba(0, 212, 170, 0.15);
        border: 1px solid rgba(0, 212, 170, 0.3);
        color: var(--stripe-green);
    }

    .risk-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        animation: pulse 2s ease infinite;
    }

    .risk-dot.high { background: var(--stripe-red); }
    .risk-dot.medium { background: var(--stripe-yellow); }
    .risk-dot.low { background: var(--stripe-green); }

    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.6; transform: scale(1.1); }
    }

    /* ===== PROGRESS BAR ===== */
    .progress-container {
        background: var(--bg-tertiary);
        border-radius: var(--radius-lg);
        padding: 2rem;
        margin: 1.5rem 0;
        border: 1px solid var(--border-subtle);
    }

    .progress-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    .progress-title {
        font-weight: 600;
        color: var(--text-primary);
    }

    .progress-percentage {
        font-size: 0.9rem;
        color: var(--stripe-purple-light);
        font-family: 'SF Mono', monospace;
    }

    .progress-bar-bg {
        height: 8px;
        background: var(--bg-secondary);
        border-radius: 4px;
        overflow: hidden;
        position: relative;
    }

    .progress-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--stripe-purple) 0%, var(--stripe-blue) 50%, var(--stripe-green) 100%);
        border-radius: 4px;
        transition: width var(--transition-normal);
        position: relative;
    }

    .progress-bar-fill::after {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        bottom: 0;
        width: 100px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        animation: shimmer 2s ease infinite;
    }

    @keyframes shimmer {
        0% { transform: translateX(-100px); }
        100% { transform: translateX(100%); }
    }

    .progress-stats {
        display: flex;
        justify-content: space-between;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid var(--border-subtle);
    }

    .progress-stat {
        text-align: center;
    }

    .progress-stat-value {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    .progress-stat-label {
        font-size: 0.75rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }

    /* ===== RESULTS TABLE ===== */
    .results-table-container {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        overflow: hidden;
    }

    .results-table {
        width: 100%;
        border-collapse: collapse;
    }

    .results-table th {
        background: var(--bg-tertiary);
        padding: 1rem 1.25rem;
        text-align: left;
        font-weight: 600;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-secondary);
        border-bottom: 1px solid var(--border-subtle);
    }

    .results-table td {
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--border-subtle);
        color: var(--text-primary);
        font-size: 0.9rem;
    }

    .results-table tr:last-child td {
        border-bottom: none;
    }

    .results-table tr:hover td {
        background: rgba(99, 91, 255, 0.03);
    }

    /* ===== BUTTONS ===== */
    .btn-primary {
        background: linear-gradient(135deg, var(--stripe-purple) 0%, var(--stripe-purple-dark) 100%);
        color: white;
        border: none;
        padding: 0.875rem 2rem;
        border-radius: var(--radius-md);
        font-weight: 600;
        font-size: 0.95rem;
        cursor: pointer;
        transition: all var(--transition-fast);
        box-shadow: 0 4px 14px rgba(99, 91, 255, 0.3);
    }

    .btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 91, 255, 0.4);
    }

    .btn-secondary {
        background: var(--bg-tertiary);
        color: var(--text-primary);
        border: 1px solid var(--border-light);
        padding: 0.75rem 1.5rem;
        border-radius: var(--radius-md);
        font-weight: 500;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all var(--transition-fast);
    }

    .btn-secondary:hover {
        border-color: var(--stripe-purple);
        background: rgba(99, 91, 255, 0.1);
    }

    /* ===== COLUMN MAPPER ===== */
    .column-mapper {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    .column-mapper-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1rem;
    }

    .column-mapper-icon {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, var(--stripe-purple) 0%, var(--stripe-blue) 100%);
        border-radius: var(--radius-sm);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
    }

    .column-mapper-title {
        font-weight: 600;
        color: var(--text-primary);
    }

    .column-mapper-subtitle {
        font-size: 0.85rem;
        color: var(--text-secondary);
    }

    .auto-detected-badge {
        background: rgba(0, 212, 170, 0.15);
        border: 1px solid rgba(0, 212, 170, 0.3);
        color: var(--stripe-green);
        padding: 0.25rem 0.5rem;
        border-radius: var(--radius-sm);
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-left: auto;
    }

    /* ===== EXPORT SECTION ===== */
    .export-options {
        display: flex;
        gap: 1rem;
        margin-top: 1.5rem;
    }

    .export-card {
        flex: 1;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 1.25rem;
        text-align: center;
        cursor: pointer;
        transition: all var(--transition-fast);
    }

    .export-card:hover {
        border-color: var(--stripe-purple);
        transform: translateY(-2px);
    }

    .export-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }

    .export-format {
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
    }

    .export-desc {
        font-size: 0.8rem;
        color: var(--text-muted);
    }

    /* ===== FILE PREVIEW ===== */
    .file-preview {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 1rem;
        margin: 1rem 0;
    }

    .file-info {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .file-icon {
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, #217346 0%, #2d8b57 100%);
        border-radius: var(--radius-sm);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
    }

    .file-details {
        flex: 1;
    }

    .file-name {
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
    }

    .file-meta {
        font-size: 0.85rem;
        color: var(--text-secondary);
    }

    .file-remove {
        color: var(--text-muted);
        cursor: pointer;
        padding: 0.5rem;
        border-radius: var(--radius-sm);
        transition: all var(--transition-fast);
    }

    .file-remove:hover {
        color: var(--stripe-red);
        background: rgba(255, 82, 82, 0.1);
    }

    /* ===== DETAILS PANEL ===== */
    .details-panel {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        overflow: hidden;
        margin-top: 1.5rem;
    }

    .details-header {
        background: var(--bg-tertiary);
        padding: 1rem 1.5rem;
        border-bottom: 1px solid var(--border-subtle);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .details-title {
        font-weight: 600;
        color: var(--text-primary);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .details-content {
        padding: 1.5rem;
    }

    .detail-row {
        display: flex;
        justify-content: space-between;
        padding: 0.75rem 0;
        border-bottom: 1px solid var(--border-subtle);
    }

    .detail-row:last-child {
        border-bottom: none;
    }

    .detail-label {
        color: var(--text-secondary);
        font-size: 0.9rem;
    }

    .detail-value {
        color: var(--text-primary);
        font-weight: 500;
    }

    /* ===== RED FLAGS LIST ===== */
    .red-flags-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .red-flag-item {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        padding: 0.75rem;
        background: rgba(255, 82, 82, 0.05);
        border: 1px solid rgba(255, 82, 82, 0.15);
        border-radius: var(--radius-sm);
        margin-bottom: 0.5rem;
    }

    .red-flag-icon {
        color: var(--stripe-red);
        font-size: 1rem;
        flex-shrink: 0;
    }

    .red-flag-text {
        color: var(--text-primary);
        font-size: 0.9rem;
        line-height: 1.4;
    }

    /* ===== ANIMATION CLASSES ===== */
    .fade-in {
        animation: fadeIn 0.4s ease forwards;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .slide-up {
        animation: slideUp 0.5s ease forwards;
    }

    @keyframes slideUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* ===== HIDE STREAMLIT ELEMENTS ===== */
    .stFileUploader > label { display: none; }

    .stFileUploader > div {
        border: none !important;
        padding: 0 !important;
    }

    div[data-testid="stFileUploader"] > section {
        padding: 0 !important;
    }

    div[data-testid="stFileUploader"] > section > div {
        display: none;
    }

    div[data-testid="stFileUploader"] > section > button {
        display: none;
    }

    /* Show file uploader input in custom area */
    .custom-upload-area div[data-testid="stFileUploader"] {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        opacity: 0;
        cursor: pointer;
    }

    .custom-upload-area {
        position: relative;
    }

    /* Override Streamlit dataframe styling */
    .stDataFrame {
        border-radius: var(--radius-lg) !important;
        overflow: hidden !important;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: var(--bg-tertiary);
        border-radius: var(--radius-md);
        padding: 0.25rem;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-sm);
        padding: 0.75rem 1.5rem;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background: var(--stripe-purple) !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Auto-detect column mappings based on column names and content.
    Returns dict with detected columns for: company_name, jurisdiction, country
    """
    columns = df.columns.tolist()
    detected = {
        'company_name': None,
        'jurisdiction': None,
        'country': None,
        'address': None,
        'registration_number': None
    }

    # Patterns for each field (order matters - first match wins)
    patterns = {
        'company_name': [
            'company_name', 'company name', 'companyname', 'name', 'company',
            'entity_name', 'entity name', 'entityname', 'business_name',
            'business name', 'businessname', 'legal_name', 'legal name',
            'organization', 'organisation', 'vendor', 'supplier', 'counterparty',
            'partner', 'client', 'customer'
        ],
        'jurisdiction': [
            'jurisdiction', 'jur', 'state', 'province', 'region',
            'incorporation_state', 'incorporation state', 'inc_state',
            'registered_state', 'formation_state'
        ],
        'country': [
            'country', 'country_code', 'country code', 'countrycode',
            'nation', 'incorporation_country', 'incorporation country',
            'registered_country', 'domicile'
        ],
        'address': [
            'address', 'registered_address', 'registered address',
            'business_address', 'business address', 'street', 'location',
            'headquarters', 'hq_address', 'office_address'
        ],
        'registration_number': [
            'registration_number', 'registration number', 'reg_number',
            'company_number', 'company number', 'ein', 'tax_id', 'tax id',
            'vat_number', 'vat number', 'crn', 'business_id'
        ]
    }

    for field, field_patterns in patterns.items():
        for col in columns:
            col_lower = col.lower().strip()
            for pattern in field_patterns:
                if pattern in col_lower or col_lower == pattern:
                    detected[field] = col
                    break
            if detected[field]:
                break

    return detected


def get_risk_color(score: int) -> str:
    """Get color based on risk score (0-100 scale, higher = better)."""
    if score >= 70:
        return "#00d4aa"  # Green - Low risk
    elif score >= 40:
        return "#ffbb00"  # Yellow - Medium risk
    else:
        return "#ff5252"  # Red - High risk


def get_risk_level(score: int) -> str:
    """Get risk level label based on score."""
    if score >= 70:
        return "LOW"
    elif score >= 40:
        return "MEDIUM"
    else:
        return "HIGH"


# ============================================================================
# CHART COMPONENTS
# ============================================================================

def create_risk_gauge(score: int, title: str = "Risk Score") -> go.Figure:
    """Create a beautiful gauge chart for risk score."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'suffix': '', 'font': {'size': 48, 'color': '#ffffff', 'family': 'Inter, sans-serif'}},
        gauge={
            'axis': {
                'range': [0, 100],
                'tickwidth': 1,
                'tickcolor': '#333344',
                'tickfont': {'color': '#666677', 'size': 10}
            },
            'bar': {'color': get_risk_color(score), 'thickness': 0.7},
            'bgcolor': '#1a1a24',
            'borderwidth': 0,
            'steps': [
                {'range': [0, 40], 'color': 'rgba(255, 82, 82, 0.1)'},
                {'range': [40, 70], 'color': 'rgba(255, 187, 0, 0.1)'},
                {'range': [70, 100], 'color': 'rgba(0, 212, 170, 0.1)'}
            ],
            'threshold': {
                'line': {'color': get_risk_color(score), 'width': 4},
                'thickness': 0.85,
                'value': score
            }
        }
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff', 'family': 'Inter, sans-serif'},
        height=280,
        margin=dict(l=30, r=30, t=40, b=20)
    )

    return fig


def create_risk_distribution(df: pd.DataFrame, score_col: str = 'risk_score') -> go.Figure:
    """Create histogram of risk score distribution."""
    if score_col not in df.columns:
        return go.Figure()

    fig = go.Figure()

    # Add histogram
    fig.add_trace(go.Histogram(
        x=df[score_col],
        nbinsx=20,
        marker=dict(
            color=df[score_col].apply(get_risk_color),
            line=dict(color='rgba(255,255,255,0.1)', width=1)
        ),
        hovertemplate='Score: %{x}<br>Count: %{y}<extra></extra>'
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff', 'family': 'Inter, sans-serif'},
        xaxis=dict(
            title='Risk Score',
            gridcolor='rgba(255,255,255,0.05)',
            tickfont={'color': '#888899'}
        ),
        yaxis=dict(
            title='Count',
            gridcolor='rgba(255,255,255,0.05)',
            tickfont={'color': '#888899'}
        ),
        height=300,
        margin=dict(l=50, r=20, t=30, b=50),
        bargap=0.1
    )

    return fig


def create_category_breakdown(results: List[Dict]) -> go.Figure:
    """Create breakdown chart by verification category."""
    categories = ['Registry', 'Sanctions', 'Offshore', 'Trade']

    # Count issues per category
    registry_issues = sum(1 for r in results if r.get('registry', {}).get('red_flags', []))
    sanctions_issues = sum(1 for r in results if r.get('sanctions', {}).get('sanctions_hits', 0) > 0)
    offshore_issues = sum(1 for r in results if r.get('offshore', {}).get('offshore_hits', 0) > 0)
    trade_issues = sum(1 for r in results if not r.get('trade', {}).get('has_trade_data', True))

    values = [registry_issues, sanctions_issues, offshore_issues, trade_issues]
    colors = ['#635bff', '#00a1ff', '#ffbb00', '#00d4aa']

    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=values,
            marker=dict(
                color=colors,
                line=dict(color='rgba(255,255,255,0.1)', width=1)
            ),
            hovertemplate='%{x}<br>Issues: %{y}<extra></extra>'
        )
    ])

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff', 'family': 'Inter, sans-serif'},
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.05)',
            tickfont={'color': '#888899'}
        ),
        yaxis=dict(
            title='Companies with Issues',
            gridcolor='rgba(255,255,255,0.05)',
            tickfont={'color': '#888899'}
        ),
        height=300,
        margin=dict(l=50, r=20, t=30, b=50)
    )

    return fig


# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_step_indicator(current_step: int):
    """Render the step progress indicator."""
    steps = [
        ("1", "Upload"),
        ("2", "Map"),
        ("3", "Process"),
        ("4", "Results")
    ]

    html = '<div class="steps-container">'

    for i, (num, label) in enumerate(steps):
        # Determine step state
        if i < current_step:
            circle_class = "completed"
            label_class = "completed"
            icon = "✓"
        elif i == current_step:
            circle_class = "active"
            label_class = "active"
            icon = num
        else:
            circle_class = "inactive"
            label_class = "inactive"
            icon = num

        html += f'''
        <div class="step">
            <div class="step-circle {circle_class}">{icon}</div>
            <div class="step-label {label_class}">{label}</div>
        </div>
        '''

        # Add connector (except after last step)
        if i < len(steps) - 1:
            if i < current_step:
                conn_class = "completed"
            elif i == current_step:
                conn_class = "active"
            else:
                conn_class = ""
            html += f'<div class="step-connector {conn_class}"></div>'

    html += '</div>'

    st.markdown(html, unsafe_allow_html=True)


def render_upload_zone():
    """Render the drag-and-drop upload zone."""
    st.markdown("""
    <div class="upload-zone">
        <div class="upload-icon">📁</div>
        <div class="upload-title">Drop your file here</div>
        <div class="upload-subtitle">or click to browse</div>
        <div class="upload-formats">
            <span class="format-badge">.xlsx</span>
            <span class="format-badge">.xls</span>
            <span class="format-badge">.csv</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_file_preview(filename: str, size: int, rows: int, cols: int):
    """Render file preview card."""
    st.markdown(f"""
    <div class="file-preview fade-in">
        <div class="file-info">
            <div class="file-icon">📊</div>
            <div class="file-details">
                <div class="file-name">{filename}</div>
                <div class="file-meta">{format_file_size(size)} • {rows:,} rows • {cols} columns</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_metric_card(value: str, label: str, delta: Optional[str] = None, delta_type: str = "neutral"):
    """Render a metric card."""
    delta_html = ""
    if delta:
        delta_html = f'<div class="metric-delta {delta_type}">{delta}</div>'

    return f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {delta_html}
    </div>
    """


def render_risk_badge(risk_level: str) -> str:
    """Render a risk badge."""
    level_lower = risk_level.lower()
    return f"""
    <span class="risk-badge {level_lower}">
        <span class="risk-dot {level_lower}"></span>
        {risk_level} Risk
    </span>
    """


def render_red_flags(flags: List[str]):
    """Render red flags list."""
    if not flags:
        st.markdown("""
        <div style="color: var(--stripe-green); padding: 1rem; background: rgba(0, 212, 170, 0.1);
                    border-radius: 8px; border: 1px solid rgba(0, 212, 170, 0.2);">
            ✓ No red flags detected
        </div>
        """, unsafe_allow_html=True)
        return

    html = '<ul class="red-flags-list">'
    for flag in flags:
        html += f'''
        <li class="red-flag-item">
            <span class="red-flag-icon">⚠</span>
            <span class="red-flag-text">{flag}</span>
        </li>
        '''
    html += '</ul>'

    st.markdown(html, unsafe_allow_html=True)


# ============================================================================
# DEMO MODE - Realistic mock data when modules unavailable
# ============================================================================

# Tax haven jurisdictions for demo
TAX_HAVENS = {'ky', 'vg', 'pa', 'bz', 'sc', 'ae', 'hk', 'sg', 'mh', 'ch', 'li', 'lu', 'mc', 'je', 'gg', 'im', 'bm', 'an', 'bs', 'ai'}

def generate_demo_result(company_name: str, jurisdiction: Optional[str], country: Optional[str]) -> Dict[str, Any]:
    """
    Generate realistic demo results based on company characteristics.
    Used when trade modules aren't available for demonstration purposes.
    """
    import random
    import hashlib

    # Use company name hash for consistent random results
    seed = int(hashlib.md5(company_name.encode()).hexdigest()[:8], 16)
    random.seed(seed)

    # Detect characteristics
    name_lower = company_name.lower()
    is_major_corp = any(x in name_lower for x in ['apple', 'microsoft', 'google', 'alphabet', 'amazon', 'tesla', 'hsbc', 'barclays', 'shell', 'bp', 'tesco'])
    is_offshore_name = any(x in name_lower for x in ['offshore', 'holdings', 'international', 'global', 'ventures', 'trading', 'investments'])
    jur_lower = (jurisdiction or country or '').lower()
    is_tax_haven = jur_lower in TAX_HAVENS or any(x in jur_lower for x in ['cayman', 'virgin', 'panama', 'seychelles', 'belize', 'marshall'])

    # Generate registry results
    if is_major_corp:
        registry = {
            'found': True,
            'status': 'Active',
            'incorporation_date': f'{random.randint(1970, 2010)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
            'officers_count': random.randint(5, 15),
            'company_type': 'Public Limited Company' if random.random() > 0.3 else 'Private Limited Company',
            'red_flags': [],
            'confidence': 0.95
        }
    elif is_tax_haven:
        registry = {
            'found': random.random() > 0.4,
            'status': 'Active' if random.random() > 0.3 else 'Unknown',
            'incorporation_date': f'{random.randint(2015, 2024)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
            'officers_count': random.randint(1, 3),
            'company_type': 'Limited Liability Company',
            'red_flags': ['Registered in tax haven jurisdiction', 'Limited public information available'],
            'confidence': 0.4
        }
        if random.random() > 0.5:
            registry['red_flags'].append('Recently incorporated (less than 2 years)')
    else:
        registry = {
            'found': random.random() > 0.2,
            'status': 'Active' if random.random() > 0.2 else 'Unknown',
            'incorporation_date': f'{random.randint(2000, 2023)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
            'officers_count': random.randint(2, 8),
            'company_type': 'Private Limited Company',
            'red_flags': [],
            'confidence': 0.7
        }

    # Generate sanctions results
    sanctions = {
        'sanctions_hits': 0,
        'pep_hits': 0,
        'matches': [],
        'confidence': 0.85,
        'red_flags': []
    }
    if is_tax_haven and random.random() > 0.7:
        sanctions['sanctions_hits'] = 1
        sanctions['red_flags'].append('Potential match found in sanctions database')
        sanctions['confidence'] = 0.6

    # Generate offshore results
    offshore = {
        'offshore_hits': 0,
        'jurisdictions': [],
        'red_flags': [],
        'entities': [],
        'confidence': 0.8
    }
    if is_tax_haven or is_offshore_name:
        if random.random() > 0.5:
            offshore['offshore_hits'] = random.randint(1, 3)
            offshore['jurisdictions'] = [jur_lower.upper() if jur_lower else 'Unknown']
            offshore['red_flags'].append('Entity found in offshore leaks database')

    # Generate trade results
    trade = {
        'has_trade_data': random.random() > 0.3,
        'country_trade_volume': random.randint(1000000, 10000000000) if country else 0,
        'importyeti_url': f'https://www.importyeti.com/company/{company_name.lower().replace(" ", "-")}',
        'confidence': 0.6
    }

    # Calculate risk score
    base_score = 50
    if is_major_corp:
        base_score = random.randint(75, 95)
    elif is_tax_haven:
        base_score = random.randint(20, 45)
    else:
        base_score = random.randint(50, 80)

    # Adjust for red flags
    total_flags = len(registry.get('red_flags', [])) + len(sanctions.get('red_flags', [])) + len(offshore.get('red_flags', []))
    base_score -= total_flags * 8

    # Clamp score
    risk_score = max(5, min(95, base_score + random.randint(-5, 5)))

    # Determine risk level
    if risk_score >= 70:
        risk_level = 'LOW'
    elif risk_score >= 40:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'HIGH'

    # Generate recommendations
    recommendations = []
    if not registry.get('found'):
        recommendations.append('Verify company registration manually through official registry')
    if sanctions.get('sanctions_hits', 0) > 0:
        recommendations.append('Conduct enhanced due diligence on sanctions match')
    if offshore.get('offshore_hits', 0) > 0:
        recommendations.append('Review offshore database entries for additional context')
    if is_tax_haven:
        recommendations.append('Consider enhanced KYC procedures for tax haven jurisdiction')
    if not recommendations:
        recommendations.append('Standard due diligence procedures apply')

    # Compile critical flags
    critical_flags = []
    if sanctions.get('sanctions_hits', 0) > 0:
        critical_flags.append('Sanctions database match')
    if not registry.get('found'):
        critical_flags.append('Company not found in registry')

    return {
        'company_name': company_name,
        'jurisdiction': jurisdiction,
        'country': country,
        'timestamp': datetime.now().isoformat(),
        'registry': registry,
        'sanctions': sanctions,
        'offshore': offshore,
        'trade': trade,
        'risk_assessment': {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'confidence': round(random.uniform(0.5, 0.9), 2),
            'critical_flags': critical_flags,
            'recommendations': recommendations
        },
        'demo_mode': True
    }


# ============================================================================
# PROCESSING FUNCTIONS
# ============================================================================

def process_company(
    company_name: str,
    jurisdiction: Optional[str] = None,
    country: Optional[str] = None,
    progress_callback=None,
    demo_mode: bool = False
) -> Dict[str, Any]:
    """
    Process a single company through all verification checks.
    Returns comprehensive verification results.

    If demo_mode is True or trade modules unavailable, returns realistic mock data.
    """
    # Use demo mode if requested or modules unavailable
    if demo_mode or not TRADE_MODULES_AVAILABLE:
        return generate_demo_result(company_name, jurisdiction, country)

    results = {
        'company_name': company_name,
        'jurisdiction': jurisdiction,
        'country': country,
        'timestamp': datetime.now().isoformat(),
        'registry': {},
        'sanctions': {},
        'offshore': {},
        'trade': {},
        'risk_assessment': {
            'risk_score': 50,
            'risk_level': 'MEDIUM',
            'confidence': 0.0,
            'critical_flags': [],
            'recommendations': []
        }
    }

    try:
        # 1. Registry Check
        if progress_callback:
            progress_callback("Checking corporate registry...")

        registry_checker = RegistryChecker()
        registry_result = registry_checker.check(company_name, jurisdiction or country)
        results['registry'] = registry_result

        # 2. Sanctions Check
        if progress_callback:
            progress_callback("Screening against sanctions lists...")

        sanctions_checker = SanctionsChecker()
        sanctions_result = sanctions_checker.check(company_name)
        results['sanctions'] = sanctions_result

        # 3. Offshore Check
        if progress_callback:
            progress_callback("Checking offshore databases...")

        offshore_checker = OffshoreChecker()
        offshore_result = offshore_checker.check(company_name)
        results['offshore'] = offshore_result

        # 4. Trade Check (if country provided)
        if country:
            if progress_callback:
                progress_callback("Verifying trade activity...")

            trade_checker = TradeChecker()
            trade_result = trade_checker.check(country)
            results['trade'] = trade_result

        # 5. Calculate Risk Score
        if progress_callback:
            progress_callback("Calculating risk assessment...")

        risk_scorer = RiskScorer()
        risk_result = risk_scorer.calculate(results)
        results['risk_assessment'] = risk_result

    except Exception as e:
        results['error'] = str(e)
        results['risk_assessment']['risk_level'] = 'UNKNOWN'

    return results


def process_batch(
    df: pd.DataFrame,
    company_col: str,
    jurisdiction_col: Optional[str] = None,
    country_col: Optional[str] = None,
    progress_container=None
) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Process a batch of companies and return results.
    Returns tuple of (results_df, detailed_results_list)
    """
    results_list = []
    total = len(df)

    for idx, row in df.iterrows():
        company_name = str(row[company_col]).strip()
        jurisdiction = str(row[jurisdiction_col]).strip() if jurisdiction_col and pd.notna(row.get(jurisdiction_col)) else None
        country = str(row[country_col]).strip() if country_col and pd.notna(row.get(country_col)) else None

        # Update progress
        if progress_container:
            progress = (idx + 1) / total
            progress_container.progress(progress)

        # Process company
        result = process_company(company_name, jurisdiction, country)
        results_list.append(result)

        # Add small delay for rate limiting
        time.sleep(0.2)

    # Convert to DataFrame
    results_df = pd.DataFrame([{
        'company_name': r['company_name'],
        'jurisdiction': r['jurisdiction'],
        'country': r['country'],
        'risk_score': r['risk_assessment'].get('risk_score', 50),
        'risk_level': r['risk_assessment'].get('risk_level', 'UNKNOWN'),
        'confidence': r['risk_assessment'].get('confidence', 0),
        'registry_found': r['registry'].get('found', False),
        'sanctions_hits': r['sanctions'].get('sanctions_hits', 0),
        'offshore_hits': r['offshore'].get('offshore_hits', 0),
        'red_flags_count': len(r.get('registry', {}).get('red_flags', []) +
                              r.get('sanctions', {}).get('red_flags', []) +
                              r.get('offshore', {}).get('red_flags', []))
    } for r in results_list])

    return results_df, results_list


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def export_to_excel(results_df: pd.DataFrame, detailed_results: List[Dict]) -> bytes:
    """Export results to Excel with multiple sheets and formatting."""
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Summary sheet
        results_df.to_excel(writer, sheet_name='Summary', index=False)

        # Detailed results sheet
        detailed_df = pd.DataFrame([{
            'company_name': r['company_name'],
            'risk_score': r['risk_assessment'].get('risk_score', 50),
            'risk_level': r['risk_assessment'].get('risk_level', 'UNKNOWN'),
            'registry_status': r['registry'].get('status', 'Unknown'),
            'registry_red_flags': '; '.join(r['registry'].get('red_flags', [])),
            'sanctions_hits': r['sanctions'].get('sanctions_hits', 0),
            'pep_hits': r['sanctions'].get('pep_hits', 0),
            'offshore_hits': r['offshore'].get('offshore_hits', 0),
            'critical_flags': '; '.join(r['risk_assessment'].get('critical_flags', [])),
            'recommendations': '; '.join(r['risk_assessment'].get('recommendations', []))
        } for r in detailed_results])
        detailed_df.to_excel(writer, sheet_name='Detailed Results', index=False)

        # Red flags sheet
        flags_data = []
        for r in detailed_results:
            company = r['company_name']
            for flag in r.get('registry', {}).get('red_flags', []):
                flags_data.append({'company': company, 'category': 'Registry', 'flag': flag})
            for flag in r.get('sanctions', {}).get('red_flags', []):
                flags_data.append({'company': company, 'category': 'Sanctions', 'flag': flag})
            for flag in r.get('offshore', {}).get('red_flags', []):
                flags_data.append({'company': company, 'category': 'Offshore', 'flag': flag})

        if flags_data:
            flags_df = pd.DataFrame(flags_data)
            flags_df.to_excel(writer, sheet_name='Red Flags', index=False)

    return buffer.getvalue()


def export_to_json(detailed_results: List[Dict]) -> str:
    """Export detailed results to JSON."""
    return json.dumps(detailed_results, indent=2, default=str)


# ============================================================================
# MAIN PAGE FUNCTION
# ============================================================================

def render_trade_verification_page():
    """Main function to render the Trade Verification page."""

    # Inject custom CSS
    inject_custom_css()

    # Page header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem;
                   background: linear-gradient(135deg, #ffffff 0%, #a0a0b0 100%);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            Trade Verification
        </h1>
        <p style="color: #888899; font-size: 1.1rem;">
            Comprehensive company verification against global registries and sanctions databases
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'tv_step' not in st.session_state:
        st.session_state.tv_step = 0
    if 'tv_df' not in st.session_state:
        st.session_state.tv_df = None
    if 'tv_results_df' not in st.session_state:
        st.session_state.tv_results_df = None
    if 'tv_detailed_results' not in st.session_state:
        st.session_state.tv_detailed_results = None
    if 'tv_column_mappings' not in st.session_state:
        st.session_state.tv_column_mappings = {}
    if 'tv_demo_mode' not in st.session_state:
        st.session_state.tv_demo_mode = not TRADE_MODULES_AVAILABLE

    # Demo mode banner
    if st.session_state.tv_demo_mode:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(99, 91, 255, 0.1) 0%, rgba(0, 161, 255, 0.1) 100%);
                    border: 1px solid rgba(99, 91, 255, 0.3); border-radius: 12px; padding: 1rem 1.5rem;
                    margin-bottom: 1.5rem; display: flex; align-items: center; gap: 1rem;">
            <span style="font-size: 1.5rem;">✨</span>
            <div>
                <div style="font-weight: 600; color: #ffffff; margin-bottom: 0.25rem;">Demo Mode Active</div>
                <div style="color: #a0a0b0; font-size: 0.9rem;">
                    Using simulated verification data. Results are realistic but not from live APIs.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Render step indicator
    render_step_indicator(st.session_state.tv_step)

    # =========================================================================
    # STEP 0: UPLOAD
    # =========================================================================
    if st.session_state.tv_step == 0:
        st.markdown("### 📁 Upload Company List")

        # Upload zone
        render_upload_zone()

        uploaded_file = st.file_uploader(
            "Upload file",
            type=["xlsx", "xls", "csv"],
            key="trade_upload",
            label_visibility="collapsed"
        )

        # Demo data option
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="text-align: center; color: #666677; font-size: 0.9rem; margin-bottom: 0.5rem;">
                or try with sample data
            </div>
            """, unsafe_allow_html=True)
            if st.button("📊 Load Demo Companies", use_container_width=True):
                # Load demo CSV
                demo_path = Path(__file__).parent.parent / "data" / "examples" / "trade_verification_demo.csv"
                if demo_path.exists():
                    demo_df = pd.read_csv(demo_path)
                    st.session_state.tv_df = demo_df
                    st.session_state.tv_filename = "trade_verification_demo.csv"
                    st.session_state.tv_filesize = demo_path.stat().st_size
                    st.session_state.tv_column_mappings = detect_columns(demo_df)
                    st.session_state.tv_demo_mode = True
                    st.session_state.tv_step = 1
                    st.rerun()
                else:
                    st.error("Demo file not found. Please upload your own file.")

        if uploaded_file is not None:
            try:
                # Load file
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)

                # Store in session state
                st.session_state.tv_df = df
                st.session_state.tv_filename = uploaded_file.name
                st.session_state.tv_filesize = uploaded_file.size

                # Auto-detect columns
                detected = detect_columns(df)
                st.session_state.tv_column_mappings = detected

                # Show file preview
                render_file_preview(
                    uploaded_file.name,
                    uploaded_file.size,
                    len(df),
                    len(df.columns)
                )

                # Show data preview
                st.markdown("#### Data Preview")
                st.dataframe(
                    df.head(5),
                    use_container_width=True,
                    height=200
                )

                # Continue button
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("Continue to Column Mapping →", type="primary", use_container_width=True):
                        st.session_state.tv_step = 1
                        st.rerun()

            except Exception as e:
                st.error(f"Error loading file: {str(e)}")

    # =========================================================================
    # STEP 1: COLUMN MAPPING
    # =========================================================================
    elif st.session_state.tv_step == 1:
        df = st.session_state.tv_df
        detected = st.session_state.tv_column_mappings

        st.markdown("### 🔗 Map Your Columns")
        st.markdown("We've auto-detected your columns. Please verify or adjust the mappings below.")

        # Column mapping cards
        col1, col2 = st.columns(2)

        with col1:
            # Company Name (Required)
            st.markdown("""
            <div class="column-mapper">
                <div class="column-mapper-header">
                    <div class="column-mapper-icon">🏢</div>
                    <div>
                        <div class="column-mapper-title">Company Name</div>
                        <div class="column-mapper-subtitle">Required field</div>
                    </div>
                    """ + (f'<span class="auto-detected-badge">Auto-detected</span>' if detected.get('company_name') else '') + """
                </div>
            </div>
            """, unsafe_allow_html=True)

            company_col = st.selectbox(
                "Select company name column",
                options=df.columns.tolist(),
                index=df.columns.tolist().index(detected['company_name']) if detected.get('company_name') in df.columns.tolist() else 0,
                key="map_company",
                label_visibility="collapsed"
            )

            # Jurisdiction (Optional)
            st.markdown("""
            <div class="column-mapper" style="margin-top: 1rem;">
                <div class="column-mapper-header">
                    <div class="column-mapper-icon">🗺️</div>
                    <div>
                        <div class="column-mapper-title">Jurisdiction / State</div>
                        <div class="column-mapper-subtitle">Optional - for US/UK registry lookup</div>
                    </div>
                    """ + (f'<span class="auto-detected-badge">Auto-detected</span>' if detected.get('jurisdiction') else '') + """
                </div>
            </div>
            """, unsafe_allow_html=True)

            jurisdiction_options = ["(None)"] + df.columns.tolist()
            default_jur_idx = jurisdiction_options.index(detected['jurisdiction']) if detected.get('jurisdiction') in jurisdiction_options else 0
            jurisdiction_col = st.selectbox(
                "Select jurisdiction column",
                options=jurisdiction_options,
                index=default_jur_idx,
                key="map_jurisdiction",
                label_visibility="collapsed"
            )

        with col2:
            # Country (Optional)
            st.markdown("""
            <div class="column-mapper">
                <div class="column-mapper-header">
                    <div class="column-mapper-icon">🌍</div>
                    <div>
                        <div class="column-mapper-title">Country</div>
                        <div class="column-mapper-subtitle">Optional - for trade data lookup</div>
                    </div>
                    """ + (f'<span class="auto-detected-badge">Auto-detected</span>' if detected.get('country') else '') + """
                </div>
            </div>
            """, unsafe_allow_html=True)

            country_options = ["(None)"] + df.columns.tolist()
            default_country_idx = country_options.index(detected['country']) if detected.get('country') in country_options else 0
            country_col = st.selectbox(
                "Select country column",
                options=country_options,
                index=default_country_idx,
                key="map_country",
                label_visibility="collapsed"
            )

            # Address (Optional)
            st.markdown("""
            <div class="column-mapper" style="margin-top: 1rem;">
                <div class="column-mapper-header">
                    <div class="column-mapper-icon">📍</div>
                    <div>
                        <div class="column-mapper-title">Address</div>
                        <div class="column-mapper-subtitle">Optional - for enhanced matching</div>
                    </div>
                    """ + (f'<span class="auto-detected-badge">Auto-detected</span>' if detected.get('address') else '') + """
                </div>
            </div>
            """, unsafe_allow_html=True)

            address_options = ["(None)"] + df.columns.tolist()
            default_addr_idx = address_options.index(detected['address']) if detected.get('address') in address_options else 0
            address_col = st.selectbox(
                "Select address column",
                options=address_options,
                index=default_addr_idx,
                key="map_address",
                label_visibility="collapsed"
            )

        # Store mappings
        st.session_state.tv_column_mappings = {
            'company_name': company_col,
            'jurisdiction': jurisdiction_col if jurisdiction_col != "(None)" else None,
            'country': country_col if country_col != "(None)" else None,
            'address': address_col if address_col != "(None)" else None
        }

        # Preview mapped data
        st.markdown("#### Mapped Data Preview")
        preview_cols = [company_col]
        if jurisdiction_col != "(None)":
            preview_cols.append(jurisdiction_col)
        if country_col != "(None)":
            preview_cols.append(country_col)

        st.dataframe(df[preview_cols].head(5), use_container_width=True, height=200)

        # Navigation buttons
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if st.button("← Back", use_container_width=True):
                st.session_state.tv_step = 0
                st.rerun()

        with col3:
            if st.button("Start Processing →", type="primary", use_container_width=True):
                st.session_state.tv_step = 2
                st.rerun()

    # =========================================================================
    # STEP 2: PROCESSING
    # =========================================================================
    elif st.session_state.tv_step == 2:
        df = st.session_state.tv_df
        mappings = st.session_state.tv_column_mappings

        st.markdown("### ⚡ Processing Companies")

        # Progress container
        st.markdown("""
        <div class="progress-container">
            <div class="progress-header">
                <span class="progress-title">Verification Progress</span>
                <span class="progress-percentage" id="progress-pct">0%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        progress_bar = st.progress(0)
        status_text = st.empty()

        # Stats row
        col1, col2, col3, col4 = st.columns(4)
        stats_containers = {
            'processed': col1.empty(),
            'high_risk': col2.empty(),
            'medium_risk': col3.empty(),
            'low_risk': col4.empty()
        }

        # Process companies
        results_list = []
        total = len(df)
        high_count = medium_count = low_count = 0

        for idx, row in df.iterrows():
            company_name = str(row[mappings['company_name']]).strip()
            jurisdiction = str(row[mappings['jurisdiction']]).strip() if mappings.get('jurisdiction') and pd.notna(row.get(mappings['jurisdiction'])) else None
            country = str(row[mappings['country']]).strip() if mappings.get('country') and pd.notna(row.get(mappings['country'])) else None

            # Update progress
            progress = (idx + 1) / total
            progress_bar.progress(progress)
            status_text.markdown(f"**Processing:** {company_name}")

            # Process company (use demo mode if set)
            demo_mode = st.session_state.get('tv_demo_mode', False)
            result = process_company(company_name, jurisdiction, country, demo_mode=demo_mode)
            results_list.append(result)

            # Update stats
            risk_level = result['risk_assessment'].get('risk_level', 'UNKNOWN')
            if risk_level == 'HIGH':
                high_count += 1
            elif risk_level == 'MEDIUM':
                medium_count += 1
            else:
                low_count += 1

            # Update stat displays
            stats_containers['processed'].markdown(render_metric_card(str(idx + 1), "Processed"), unsafe_allow_html=True)
            stats_containers['high_risk'].markdown(render_metric_card(str(high_count), "High Risk", delta_type="negative"), unsafe_allow_html=True)
            stats_containers['medium_risk'].markdown(render_metric_card(str(medium_count), "Medium Risk", delta_type="neutral"), unsafe_allow_html=True)
            stats_containers['low_risk'].markdown(render_metric_card(str(low_count), "Low Risk", delta_type="positive"), unsafe_allow_html=True)

            # Rate limiting (faster in demo mode)
            time.sleep(0.15 if demo_mode else 0.3)

        # Convert to DataFrame
        results_df = pd.DataFrame([{
            'company_name': r['company_name'],
            'jurisdiction': r['jurisdiction'],
            'country': r['country'],
            'risk_score': r['risk_assessment'].get('risk_score', 50),
            'risk_level': r['risk_assessment'].get('risk_level', 'UNKNOWN'),
            'confidence': r['risk_assessment'].get('confidence', 0),
            'registry_found': r['registry'].get('found', False),
            'registry_status': r['registry'].get('status', 'Unknown'),
            'sanctions_hits': r['sanctions'].get('sanctions_hits', 0),
            'pep_hits': r['sanctions'].get('pep_hits', 0),
            'offshore_hits': r['offshore'].get('offshore_hits', 0),
            'red_flags_count': len(r.get('registry', {}).get('red_flags', []) +
                                  r.get('sanctions', {}).get('red_flags', []) +
                                  r.get('offshore', {}).get('red_flags', []))
        } for r in results_list])

        # Store results
        st.session_state.tv_results_df = results_df
        st.session_state.tv_detailed_results = results_list

        # Completion message
        status_text.markdown("**✓ Processing complete!**")

        # Auto-advance to results
        time.sleep(1)
        st.session_state.tv_step = 3
        st.rerun()

    # =========================================================================
    # STEP 3: RESULTS
    # =========================================================================
    elif st.session_state.tv_step == 3:
        results_df = st.session_state.tv_results_df
        detailed_results = st.session_state.tv_detailed_results

        st.markdown("### 📊 Verification Results")

        # Summary metrics row
        total_companies = len(results_df)
        high_risk = len(results_df[results_df['risk_level'] == 'HIGH'])
        medium_risk = len(results_df[results_df['risk_level'] == 'MEDIUM'])
        low_risk = len(results_df[results_df['risk_level'] == 'LOW'])
        avg_score = results_df['risk_score'].mean()

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.markdown(render_metric_card(str(total_companies), "Total Companies"), unsafe_allow_html=True)
        with col2:
            st.markdown(render_metric_card(str(high_risk), "High Risk", delta_type="negative"), unsafe_allow_html=True)
        with col3:
            st.markdown(render_metric_card(str(medium_risk), "Medium Risk", delta_type="neutral"), unsafe_allow_html=True)
        with col4:
            st.markdown(render_metric_card(str(low_risk), "Low Risk", delta_type="positive"), unsafe_allow_html=True)
        with col5:
            st.markdown(render_metric_card(f"{avg_score:.0f}", "Avg Score"), unsafe_allow_html=True)

        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["📋 Results Table", "📈 Analytics", "🔍 Company Details"])

        with tab1:
            # Filter controls
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                risk_filter = st.multiselect(
                    "Filter by Risk Level",
                    options=['HIGH', 'MEDIUM', 'LOW'],
                    default=['HIGH', 'MEDIUM', 'LOW']
                )

            with col2:
                search_term = st.text_input("Search companies", placeholder="Type to search...")

            # Apply filters
            filtered_df = results_df[results_df['risk_level'].isin(risk_filter)]
            if search_term:
                filtered_df = filtered_df[filtered_df['company_name'].str.contains(search_term, case=False, na=False)]

            # Styled dataframe
            def style_risk_row(row):
                if row['risk_level'] == 'HIGH':
                    return ['background-color: rgba(255, 82, 82, 0.1)'] * len(row)
                elif row['risk_level'] == 'MEDIUM':
                    return ['background-color: rgba(255, 187, 0, 0.1)'] * len(row)
                else:
                    return ['background-color: rgba(0, 212, 170, 0.1)'] * len(row)

            display_cols = ['company_name', 'risk_score', 'risk_level', 'registry_found',
                           'sanctions_hits', 'offshore_hits', 'red_flags_count']

            styled_df = filtered_df[display_cols].style.apply(style_risk_row, axis=1)
            st.dataframe(styled_df, use_container_width=True, height=400)

        with tab2:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Risk Score Distribution")
                fig = create_risk_distribution(results_df)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("#### Issues by Category")
                fig = create_category_breakdown(detailed_results)
                st.plotly_chart(fig, use_container_width=True)

            # Risk level breakdown
            st.markdown("#### Risk Level Breakdown")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""
                <div style="background: rgba(255, 82, 82, 0.1); border: 1px solid rgba(255, 82, 82, 0.3);
                            border-radius: 12px; padding: 1.5rem; text-align: center;">
                    <div style="font-size: 2.5rem; font-weight: 700; color: #ff5252;">{high_risk}</div>
                    <div style="color: #ff7070; font-weight: 500;">High Risk</div>
                    <div style="color: #888899; font-size: 0.85rem; margin-top: 0.5rem;">
                        {(high_risk/total_companies*100):.1f}% of total
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div style="background: rgba(255, 187, 0, 0.1); border: 1px solid rgba(255, 187, 0, 0.3);
                            border-radius: 12px; padding: 1.5rem; text-align: center;">
                    <div style="font-size: 2.5rem; font-weight: 700; color: #ffbb00;">{medium_risk}</div>
                    <div style="color: #ffcc33; font-weight: 500;">Medium Risk</div>
                    <div style="color: #888899; font-size: 0.85rem; margin-top: 0.5rem;">
                        {(medium_risk/total_companies*100):.1f}% of total
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                <div style="background: rgba(0, 212, 170, 0.1); border: 1px solid rgba(0, 212, 170, 0.3);
                            border-radius: 12px; padding: 1.5rem; text-align: center;">
                    <div style="font-size: 2.5rem; font-weight: 700; color: #00d4aa;">{low_risk}</div>
                    <div style="color: #1aea9f; font-weight: 500;">Low Risk</div>
                    <div style="color: #888899; font-size: 0.85rem; margin-top: 0.5rem;">
                        {(low_risk/total_companies*100):.1f}% of total
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with tab3:
            # Company selector
            selected_company = st.selectbox(
                "Select a company to view details",
                options=results_df['company_name'].tolist(),
                key="company_detail_select"
            )

            if selected_company:
                # Find detailed result
                company_result = next((r for r in detailed_results if r['company_name'] == selected_company), None)

                if company_result:
                    risk_score = company_result['risk_assessment'].get('risk_score', 50)
                    risk_level = company_result['risk_assessment'].get('risk_level', 'UNKNOWN')

                    col1, col2 = st.columns([1, 2])

                    with col1:
                        # Risk gauge
                        fig = create_risk_gauge(risk_score)
                        st.plotly_chart(fig, use_container_width=True)

                        st.markdown(f"""
                        <div style="text-align: center;">
                            {render_risk_badge(risk_level)}
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        # Verification details
                        st.markdown("#### Verification Summary")

                        # Registry
                        registry = company_result.get('registry', {})
                        with st.expander("🏢 Corporate Registry", expanded=True):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown(f"**Status:** {registry.get('status', 'Unknown')}")
                                st.markdown(f"**Found:** {'✓ Yes' if registry.get('found') else '✗ No'}")
                            with col_b:
                                st.markdown(f"**Officers:** {registry.get('officers_count', 'N/A')}")
                                st.markdown(f"**Incorporation:** {registry.get('incorporation_date', 'N/A')}")

                            if registry.get('red_flags'):
                                st.markdown("**Red Flags:**")
                                render_red_flags(registry.get('red_flags', []))

                        # Sanctions
                        sanctions = company_result.get('sanctions', {})
                        with st.expander("🚫 Sanctions Screening"):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown(f"**Sanctions Hits:** {sanctions.get('sanctions_hits', 0)}")
                            with col_b:
                                st.markdown(f"**PEP Hits:** {sanctions.get('pep_hits', 0)}")

                            if sanctions.get('red_flags'):
                                st.markdown("**Red Flags:**")
                                render_red_flags(sanctions.get('red_flags', []))

                        # Offshore
                        offshore = company_result.get('offshore', {})
                        with st.expander("🏝️ Offshore Database"):
                            st.markdown(f"**Offshore Hits:** {offshore.get('offshore_hits', 0)}")

                            if offshore.get('jurisdictions'):
                                st.markdown(f"**Jurisdictions:** {', '.join(offshore.get('jurisdictions', []))}")

                            if offshore.get('red_flags'):
                                st.markdown("**Red Flags:**")
                                render_red_flags(offshore.get('red_flags', []))

                        # Recommendations
                        recommendations = company_result['risk_assessment'].get('recommendations', [])
                        if recommendations:
                            st.markdown("#### Recommendations")
                            for rec in recommendations:
                                st.markdown(f"• {rec}")

        # Export section
        st.markdown("---")
        st.markdown("### 📥 Export Results")

        col1, col2, col3 = st.columns(3)

        with col1:
            excel_data = export_to_excel(results_df, detailed_results)
            st.download_button(
                label="📊 Download Excel",
                data=excel_data,
                file_name=f"trade_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with col2:
            csv_data = results_df.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV",
                data=csv_data,
                file_name=f"trade_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col3:
            json_data = export_to_json(detailed_results)
            st.download_button(
                label="🔧 Download JSON",
                data=json_data,
                file_name=f"trade_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )

        # Start over button
        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔄 Start New Verification", use_container_width=True):
                # Clear session state
                st.session_state.tv_step = 0
                st.session_state.tv_df = None
                st.session_state.tv_results_df = None
                st.session_state.tv_detailed_results = None
                st.session_state.tv_column_mappings = {}
                st.rerun()


# ============================================================================
# STANDALONE ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    st.set_page_config(
        page_title="Trade Verification",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    render_trade_verification_page()
