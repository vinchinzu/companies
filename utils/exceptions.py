"""Custom exceptions for the Company Research Tool.

Provides standardized error types for consistent error handling
across all modules.
"""


class CompanyResearchError(Exception):
    """Base exception for all Company Research Tool errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DataLoadError(CompanyResearchError):
    """Failed to load data from file or external source."""
    pass


class APIError(CompanyResearchError):
    """API request failed."""
    
    def __init__(self, api_name: str, message: str, status_code: int = None, details: dict = None):
        super().__init__(message, details)
        self.api_name = api_name
        self.status_code = status_code


class ValidationError(CompanyResearchError):
    """Input validation failed."""
    pass


class EnrichmentError(CompanyResearchError):
    """Company data enrichment failed."""
    pass


class ScoringError(CompanyResearchError):
    """Risk scoring computation failed."""
    pass


class FileOperationError(CompanyResearchError):
    """File read/write operation failed."""
    pass


def handle_api_error(api_name: str, error: Exception) -> APIError:
    """Convert exception to APIError with proper context."""
    import requests
    
    if isinstance(error, requests.HTTPError):
        return APIError(
            api_name=api_name,
            message=str(error),
            status_code=error.response.status_code if error.response else None,
        )
    elif isinstance(error, requests.Timeout):
        return APIError(
            api_name=api_name,
            message=f"Request timed out: {error}",
        )
    elif isinstance(error, requests.ConnectionError):
        return APIError(
            api_name=api_name,
            message=f"Connection error: {error}",
        )
    else:
        return APIError(
            api_name=api_name,
            message=str(error),
        )


def validate_file_upload(uploaded_file, allowed_types: list = None) -> None:
    """Validate uploaded file before processing.
    
    Args:
        uploaded_file: Streamlit uploaded file object
        allowed_types: List of allowed file extensions (e.g., ['.csv', '.xlsx'])
    
    Raises:
        ValidationError: If file is invalid
    """
    if uploaded_file is None:
        raise ValidationError("No file uploaded")
    
    if not hasattr(uploaded_file, 'name'):
        raise ValidationError("Invalid file object")
    
    filename = uploaded_file.name.lower()
    
    if allowed_types:
        if not any(filename.endswith(ext) for ext in allowed_types):
            raise ValidationError(
                f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )
    
    # Check file size (max 10MB)
    MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    if hasattr(uploaded_file, 'size') and uploaded_file.size and uploaded_file.size > MAX_SIZE:
        raise ValidationError(
            f"File too large. Maximum size: {MAX_SIZE // (1024*1024)}MB"
        )


def validate_column_exists(df, column_name: str) -> None:
    """Validate that required column exists in DataFrame.
    
    Args:
        df: pandas DataFrame
        column_name: Name of required column
    
    Raises:
        ValidationError: If column missing
    """
    if column_name not in df.columns:
        raise ValidationError(
            f"Column '{column_name}' not found. Available columns: {list(df.columns)}"
        )


def validate_dataframe(df, min_rows: int = 1, required_columns: list = None) -> None:
    """Validate DataFrame has required structure.
    
    Args:
        df: pandas DataFrame to validate
        min_rows: Minimum number of rows required
        required_columns: List of required column names
    
    Raises:
        ValidationError: If DataFrame fails validation
    """
    if df is None:
        raise ValidationError("DataFrame is None")
    
    if len(df) < min_rows:
        raise ValidationError(
            f"DataFrame has only {len(df)} rows. Minimum required: {min_rows}"
        )
    
    if required_columns:
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValidationError(
                f"Missing required columns: {missing}"
            )
