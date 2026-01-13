"""Typed session state wrapper for Streamlit.

Provides type-safe access to session state with validation.
"""

from typing import Any, Optional, TypeVar, Generic

import streamlit as st

T = TypeVar('T')


class SessionStateWrapper(Generic[T]):
    """Wrapper for type-safe session state access.
    
    Usage:
        analysis_results = SessionStateWrapper[pd.DataFrame](
            "analysis_results", default=None
        )
        
        # Get value
        df = analysis_results.get()
        
        # Set value
        analysis_results.set(new_df)
        
        # Clear
        analysis_results.clear()
    """
    
    def __init__(self, key: str, default: Optional[T] = None):
        """Initialize wrapper for a session state key.
        
        Args:
            key: Session state key
            default: Default value if key not set
        """
        self._key = key
        self._default = default
    
    def get(self) -> Optional[T]:
        """Get current value from session state."""
        return st.session_state.get(self._key, self._default)
    
    def set(self, value: T) -> None:
        """Set value in session state."""
        st.session_state[self._key] = value
    
    def clear(self) -> None:
        """Remove key from session state."""
        if self._key in st.session_state:
            del st.session_state[self._key]
    
    def exists(self) -> bool:
        """Check if key exists in session state."""
        return self._key in st.session_state
    
    def update(self, **kwargs) -> None:
        """Update multiple fields at once.
        
        Only updates fields that are currently set.
        """
        current = self.get() or {}
        if isinstance(current, dict):
            current.update(kwargs)
            self.set(current)
    
    def get_or_init(self, factory) -> T:
        """Get value or initialize with factory function.
        
        Args:
            factory: Function that creates initial value
        
        Returns:
            Existing value or newly initialized value
        """
        if not self.exists():
            self.set(factory())
        return self.get()


# Pre-defined session state wrappers for common use cases
class AnalysisState:
    """Session state keys for analysis results."""
    
    RESULTS = SessionStateWrapper[list[dict]]("analysis_results", default=None)
    ENRICHED_DATA = SessionStateWrapper[list[dict]]("enriched_data", default=None)
    SCORED_DATA = SessionStateWrapper[list[dict]]("scored_data", default=None)
    
    @staticmethod
    def clear_all() -> None:
        """Clear all analysis state."""
        AnalysisState.RESULTS.clear()
        AnalysisState.ENRICHED_DATA.clear()
        AnalysisState.SCORED_DATA.clear()
    
    @staticmethod
    def set_results(results: list[dict]) -> None:
        """Set analysis results and derived data."""
        AnalysisState.RESULTS.set(results)
        # Could derive additional state here if needed
    
    @staticmethod
    def get_results() -> Optional[list[dict]]:
        """Get analysis results."""
        return AnalysisState.RESULTS.get()


class SanctionsState:
    """Session state for sanctions screening."""
    
    LAST_QUERY = SessionStateWrapper[str]("sanctions_last_query", default=None)
    LAST_RESULTS = SessionStateWrapper[list[dict]]("sanctions_last_results", default=None)


class UISettings:
    """Session state for UI preferences."""
    
    DARK_MODE = SessionStateWrapper[bool]("ui_dark_mode", default=False)
    EXPANDED_DETAILS = SessionStateWrapper[bool]("ui_expanded_details", default=True)
    
    @staticmethod
    def toggle_dark_mode() -> bool:
        """Toggle dark mode and return new state."""
        new_value = not UISettings.DARK_MODE.get()
        UISettings.DARK_MODE.set(new_value)
        return new_value


def initialize_session_state() -> None:
    """Initialize default session state values.
    
    Call this once at app start.
    """
    if "initialized" not in st.session_state:
        st.session_state["initialized"] = True
        # Set defaults
        UISettings.DARK_MODE.set(False)
        UISettings.EXPANDED_DETAILS.set(True)


def clear_all_state() -> None:
    """Clear all session state (useful for logout/reset)."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session_state()
