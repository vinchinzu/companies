"""OpenCorporates API integration for corporate registry data."""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import requests

from config import OPENCORPORATES_API_TOKEN, OPENCORPORATES_URL, RATE_LIMIT_DELAY


@dataclass
class Officer:
    """Company officer/director information."""

    name: str
    position: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    address: Optional[str] = None
    nationality: Optional[str] = None


@dataclass
class CorporateData:
    """Corporate registry data for a company."""

    name: str
    company_number: Optional[str] = None
    jurisdiction: Optional[str] = None
    incorporation_date: Optional[str] = None
    dissolution_date: Optional[str] = None
    status: Optional[str] = None
    company_type: Optional[str] = None
    registered_address: Optional[str] = None
    officers: list[Officer] = field(default_factory=list)
    previous_names: list[str] = field(default_factory=list)
    industry_codes: list[str] = field(default_factory=list)
    lifespan_days: Optional[int] = None
    source_url: Optional[str] = None
    error: Optional[str] = None


class OpenCorporatesClient:
    """Client for OpenCorporates API."""

    def __init__(self, api_token: Optional[str] = None, delay: float = None):
        """Initialize OpenCorporates client.

        Args:
            api_token: OpenCorporates API token. Defaults to config value.
            delay: Delay between requests in seconds.
        """
        self.api_token = api_token or OPENCORPORATES_API_TOKEN
        self.delay = delay if delay is not None else RATE_LIMIT_DELAY
        self.session = requests.Session()

    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make API request to OpenCorporates."""
        url = f"{OPENCORPORATES_URL}{endpoint}"

        if params is None:
            params = {}

        if self.api_token:
            params["api_token"] = self.api_token

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            time.sleep(self.delay)
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def _calculate_lifespan(self, inc_date: Optional[str]) -> Optional[int]:
        """Calculate company lifespan in days."""
        if not inc_date:
            return None

        try:
            inc = datetime.fromisoformat(inc_date.replace("Z", "+00:00"))
            return (datetime.now(inc.tzinfo) - inc).days
        except (ValueError, AttributeError):
            try:
                inc = datetime.strptime(inc_date, "%Y-%m-%d")
                return (datetime.now() - inc).days
            except ValueError:
                return None

    def _parse_officers(self, officers_data: list) -> list[Officer]:
        """Parse officers from API response."""
        officers = []

        for item in officers_data:
            officer_data = item.get("officer", {})
            officers.append(
                Officer(
                    name=officer_data.get("name", "Unknown"),
                    position=officer_data.get("position"),
                    start_date=officer_data.get("start_date"),
                    end_date=officer_data.get("end_date"),
                    address=officer_data.get("address"),
                    nationality=officer_data.get("nationality"),
                )
            )

        return officers

    def _parse_address(self, address_data: Optional[dict]) -> Optional[str]:
        """Parse address from API response."""
        if not address_data:
            return None

        parts = [
            address_data.get("street_address"),
            address_data.get("locality"),
            address_data.get("region"),
            address_data.get("postal_code"),
            address_data.get("country"),
        ]

        return ", ".join(p for p in parts if p)

    def search_companies(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        per_page: int = 10,
    ) -> list[CorporateData]:
        """Search for companies by name.

        Args:
            query: Company name to search
            jurisdiction: Optional jurisdiction code to filter
            per_page: Results per page (max 100)

        Returns:
            List of CorporateData objects
        """
        params = {"q": query, "per_page": min(per_page, 100)}

        if jurisdiction:
            params["jurisdiction_code"] = jurisdiction.lower()

        data = self._make_request("/companies/search", params)

        if "error" in data:
            return [CorporateData(name=query, error=data["error"])]

        results = []
        companies = data.get("results", {}).get("companies", [])

        for item in companies:
            company = item.get("company", {})
            results.append(
                CorporateData(
                    name=company.get("name", ""),
                    company_number=company.get("company_number"),
                    jurisdiction=company.get("jurisdiction_code"),
                    incorporation_date=company.get("incorporation_date"),
                    dissolution_date=company.get("dissolution_date"),
                    status=company.get("current_status"),
                    company_type=company.get("company_type"),
                    registered_address=self._parse_address(
                        company.get("registered_address")
                    ),
                    previous_names=[
                        n.get("company_name", "")
                        for n in company.get("previous_names", [])
                    ],
                    industry_codes=[
                        c.get("code", "")
                        for c in company.get("industry_codes", [])
                    ],
                    lifespan_days=self._calculate_lifespan(
                        company.get("incorporation_date")
                    ),
                    source_url=company.get("opencorporates_url"),
                )
            )

        return results

    def get_company_details(
        self,
        jurisdiction_code: str,
        company_number: str,
    ) -> CorporateData:
        """Get detailed company information including officers.

        Args:
            jurisdiction_code: Jurisdiction code (e.g., 'us_de', 'gb')
            company_number: Company registration number

        Returns:
            CorporateData with full details including officers
        """
        endpoint = f"/companies/{jurisdiction_code.lower()}/{company_number}"
        data = self._make_request(endpoint)

        if "error" in data:
            return CorporateData(
                name="Unknown",
                company_number=company_number,
                jurisdiction=jurisdiction_code,
                error=data["error"],
            )

        company = data.get("results", {}).get("company", {})

        return CorporateData(
            name=company.get("name", ""),
            company_number=company.get("company_number"),
            jurisdiction=company.get("jurisdiction_code"),
            incorporation_date=company.get("incorporation_date"),
            dissolution_date=company.get("dissolution_date"),
            status=company.get("current_status"),
            company_type=company.get("company_type"),
            registered_address=self._parse_address(
                company.get("registered_address")
            ),
            officers=self._parse_officers(company.get("officers", [])),
            previous_names=[
                n.get("company_name", "") for n in company.get("previous_names", [])
            ],
            industry_codes=[
                c.get("code", "") for c in company.get("industry_codes", [])
            ],
            lifespan_days=self._calculate_lifespan(company.get("incorporation_date")),
            source_url=company.get("opencorporates_url"),
        )

    def search_officers(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        per_page: int = 10,
    ) -> list[Officer]:
        """Search for officers by name.

        Args:
            query: Officer name to search
            jurisdiction: Optional jurisdiction code
            per_page: Results per page

        Returns:
            List of Officer objects
        """
        params = {"q": query, "per_page": min(per_page, 100)}

        if jurisdiction:
            params["jurisdiction_code"] = jurisdiction.lower()

        data = self._make_request("/officers/search", params)

        if "error" in data:
            return []

        officers = []
        results = data.get("results", {}).get("officers", [])

        for item in results:
            officer = item.get("officer", {})
            officers.append(
                Officer(
                    name=officer.get("name", "Unknown"),
                    position=officer.get("position"),
                    start_date=officer.get("start_date"),
                    end_date=officer.get("end_date"),
                )
            )

        return officers

    def get_mock_corporate_data(self, company_name: str) -> CorporateData:
        """Return mock data when no API key is available (for demo)."""
        import random

        jurisdictions = ["us_de", "us_ca", "gb", "sg", "ky", "vg", "pa"]
        statuses = ["Active", "Active", "Active", "Inactive", "Dissolved"]

        is_shell = random.random() > 0.6

        if is_shell:
            # Suspicious profile
            jur = random.choice(["ky", "vg", "pa", "bz"])
            days_ago = random.randint(30, 365)
            inc_date = (
                datetime.now()
                - __import__("datetime").timedelta(days=days_ago)
            ).strftime("%Y-%m-%d")
            officers = []
            if random.random() > 0.5:
                officers = [
                    Officer(name="John Doe", position="Director"),
                ]
        else:
            # Legitimate profile
            jur = random.choice(["us_de", "us_ca", "us_ny", "gb"])
            days_ago = random.randint(365 * 2, 365 * 20)
            inc_date = (
                datetime.now()
                - __import__("datetime").timedelta(days=days_ago)
            ).strftime("%Y-%m-%d")
            officers = [
                Officer(name=f"Officer {i}", position="Director")
                for i in range(random.randint(2, 5))
            ]

        return CorporateData(
            name=company_name,
            company_number=f"C{random.randint(1000000, 9999999)}",
            jurisdiction=jur,
            incorporation_date=inc_date,
            status=random.choice(statuses),
            company_type="Corporation" if random.random() > 0.3 else "LLC",
            registered_address="123 Main St, City, Country" if not is_shell else None,
            officers=officers,
            lifespan_days=days_ago,
        )

    def search_or_mock(
        self,
        company_name: str,
        jurisdiction: Optional[str] = None,
    ) -> list[CorporateData]:
        """Search for company, falling back to mock data if no API key."""
        if self.api_token:
            results = self.search_companies(company_name, jurisdiction)
            if results and not results[0].error:
                return results

        # Return mock data
        return [self.get_mock_corporate_data(company_name)]
