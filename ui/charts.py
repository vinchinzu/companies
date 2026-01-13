"""Chart components for the Company Research Tool.

Provides reusable Plotly chart functions with consistent styling.
"""

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Risk level colors (consistent across app)
RISK_COLORS = {
    "Low Risk": "green",
    "Medium Risk": "orange", 
    "High Risk": "red",
}

# Risk gauge colors by score
def _get_gauge_color(score: float) -> str:
    if score >= 3.0:
        return "green"
    elif score >= 2.0:
        return "orange"
    return "red"


def create_risk_gauge(score: float, title: str = "Risk Score") -> go.Figure:
    """Create a gauge chart for risk score.
    
    Args:
        score: Risk score (0-4 scale)
        title: Title for the gauge
    
    Returns:
        Plotly Figure with gauge chart
    """
    color = _get_gauge_color(score)
    
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": title},
            gauge={
                "axis": {"range": [0, 4], "tickwidth": 1},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 2], "color": "lightcoral"},
                    {"range": [2, 3], "color": "lightyellow"},
                    {"range": [3, 4], "color": "lightgreen"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 4},
                    "thickness": 0.75,
                    "value": score,
                },
            },
        )
    )
    fig.update_layout(height=250, margin=dict(t=50, b=0, l=20, r=20))
    return fig


def create_category_breakdown(data: dict[str, Any]) -> go.Figure:
    """Create a bar chart showing category score breakdown.
    
    Args:
        data: Dict with category scores
    
    Returns:
        Plotly Figure with bar chart
    """
    categories = [
        "Online Activity",
        "Corporate Info",
        "Officers",
        "Jurisdiction",
        "External",
    ]
    score_keys = [
        "online_activity_score",
        "corporate_info_score",
        "officers_structure_score",
        "jurisdiction_risk_score",
        "external_factors_score",
    ]
    scores = [data.get(key, 0) for key in score_keys]
    
    colors = ["green" if s >= 3 else "orange" if s >= 2 else "red" for s in scores]
    
    fig = go.Figure(
        data=[
            go.Bar(
                x=categories,
                y=scores,
                marker_color=colors,
                text=[f"{s:.1f}" for s in scores],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title="Category Score Breakdown",
        yaxis=dict(range=[0, 4.5], title="Score (0-4)"),
        height=300,
        margin=dict(t=50, b=50),
    )
    return fig


def create_risk_distribution(df: pd.DataFrame) -> go.Figure:
    """Create a histogram of risk scores.
    
    Args:
        df: DataFrame with 'risk_score' and 'risk_level' columns
    
    Returns:
        Plotly Figure with histogram
    """
    fig = px.histogram(
        df,
        x="risk_score",
        nbins=20,
        color="risk_level",
        color_discrete_map=RISK_COLORS,
        title="Risk Score Distribution",
    )
    fig.update_layout(
        xaxis_title="Risk Score (0-4)",
        yaxis_title="Count",
        height=300,
    )
    return fig


def create_source_breakdown(source_counts: pd.Series, title: str = "Records by Source") -> go.Figure:
    """Create a pie chart showing source breakdown.
    
    Args:
        source_counts: Series with source names as index and counts as values
        title: Chart title
    
    Returns:
        Plotly Figure with pie chart
    """
    fig = px.pie(
        values=source_counts.values,
        names=source_counts.index,
        title=title,
        hole=0.4,
    )
    fig.update_layout(height=350)
    return fig


def create_jurisdiction_chart(jur_counts: pd.Series, title: str = "Top Jurisdictions") -> go.Figure:
    """Create a bar chart for jurisdiction counts.
    
    Args:
        jur_counts: Series with jurisdiction codes as index and counts as values
        title: Chart title
    
    Returns:
        Plotly Figure with bar chart
    """
    fig = px.bar(
        x=jur_counts.index,
        y=jur_counts.values,
        title=title,
        labels={"x": "Jurisdiction", "y": "Count"},
    )
    fig.update_layout(height=300)
    return fig


def create_fraud_type_pie(type_counts: pd.Series, title: str = "Fraud Types Distribution") -> go.Figure:
    """Create a pie chart for fraud type breakdown.
    
    Args:
        type_counts: Series with fraud types as index and counts as values
        title: Chart title
    
    Returns:
        Plotly Figure with pie chart
    """
    fig = px.pie(
        values=type_counts.values,
        names=type_counts.index,
        title=title,
    )
    fig.update_layout(height=350)
    return fig


def create_risk_level_bar_summary(
    high_count: int, 
    medium_count: int, 
    low_count: int
) -> go.Figure:
    """Create summary bar chart for risk level counts.
    
    Args:
        high_count: Number of high risk companies
        medium_count: Number of medium risk companies
        low_count: Number of low risk companies
    
    Returns:
        Plotly Figure with bar chart
    """
    fig = go.Figure(
        data=[
            go.Bar(
                x=["High Risk", "Medium Risk", "Low Risk"],
                y=[high_count, medium_count, low_count],
                marker_color=["red", "orange", "green"],
                text=[high_count, medium_count, low_count],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title="Risk Level Summary",
        yaxis_title="Count",
        height=250,
    )
    return fig


def highlight_risk_row(row: pd.Series) -> list[str]:
    """Generate row styling for risk level.
    
    Args:
        row: DataFrame row with 'risk_level' key
    
    Returns:
        List of CSS style strings for each cell
    """
    risk_level = row.get("risk_level", "")
    if risk_level == "High Risk":
        return ["background-color: #ffcccb"] * len(row)
    elif risk_level == "Medium Risk":
        return ["background-color: #ffffcc"] * len(row)
    return ["background-color: #ccffcc"] * len(row)


def highlight_status_row(row: pd.Series) -> list[str]:
    """Generate row styling for sanctions screening status.
    
    Args:
        row: DataFrame row with 'status' key
    
    Returns:
        List of CSS style strings for each cell
    """
    status = row.get("status", "")
    if status == "EXACT MATCH":
        return ["background-color: #ff6b6b"] * len(row)
    elif status == "PARTIAL MATCH":
        return ["background-color: #ffd93d"] * len(row)
    return ["background-color: #6bcb77"] * len(row)
