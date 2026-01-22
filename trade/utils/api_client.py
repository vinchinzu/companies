"""
Base API client with retry logic, rate limiting, and error handling.
"""

import time
import requests
from typing import Optional, Dict, Any
from config import Config


class APIClient:
    """
    Base API client with built-in retry logic and rate limiting.
    """

    def __init__(self, base_url: str, rate_limit: Optional[float] = None, timeout: int = None):
        """
        Initialize API client.

        Args:
            base_url: Base URL for the API
            rate_limit: Maximum requests per second (None = no limit)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.rate_limit = rate_limit
        self.timeout = timeout or Config.API_TIMEOUT
        self.last_request_time = 0
        self.session = requests.Session()

    def _rate_limit_wait(self):
        """Enforce rate limiting between requests."""
        if self.rate_limit:
            time_since_last = time.time() - self.last_request_time
            min_interval = 1.0 / self.rate_limit
            if time_since_last < min_interval:
                time.sleep(min_interval - time_since_last)
        self.last_request_time = time.time()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        json_data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
            headers: HTTP headers
            auth: Authentication tuple (username, password)
            json_data: JSON request body

        Returns:
            Response JSON or None on failure
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(Config.MAX_RETRIES):
            try:
                # Enforce rate limiting
                self._rate_limit_wait()

                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    auth=auth,
                    json=json_data,
                    timeout=self.timeout
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue

                # Raise for other HTTP errors
                response.raise_for_status()

                # Return JSON response
                return response.json() if response.content else {}

            except requests.exceptions.Timeout:
                print(f"Request timeout (attempt {attempt + 1}/{Config.MAX_RETRIES})")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_BACKOFF ** attempt)
                    continue
                return None

            except requests.exceptions.HTTPError as e:
                # Don't retry on client errors (4xx except 429)
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    print(f"Client error: {e.response.status_code} - {e.response.text}")
                    return None

                # Retry on server errors (5xx)
                print(f"Server error (attempt {attempt + 1}/{Config.MAX_RETRIES}): {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_BACKOFF ** attempt)
                    continue
                return None

            except requests.exceptions.RequestException as e:
                print(f"Request failed (attempt {attempt + 1}/{Config.MAX_RETRIES}): {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_BACKOFF ** attempt)
                    continue
                return None

        return None

    def get(self, endpoint: str, params: Optional[Dict] = None, headers: Optional[Dict] = None, auth: Optional[tuple] = None) -> Optional[Dict]:
        """Make GET request."""
        return self._make_request('GET', endpoint, params=params, headers=headers, auth=auth)

    def post(self, endpoint: str, json_data: Optional[Dict] = None, headers: Optional[Dict] = None, auth: Optional[tuple] = None) -> Optional[Dict]:
        """Make POST request."""
        return self._make_request('POST', endpoint, json_data=json_data, headers=headers, auth=auth)

    def close(self):
        """Close the session."""
        self.session.close()
