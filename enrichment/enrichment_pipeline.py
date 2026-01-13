"""Enrichment pipeline combining all data sources."""

from dataclasses import dataclass, field, asdict
from typing import Optional

from .brave_search import BraveSearchClient, OnlinePresence
from .opencorporates import OpenCorporatesClient, CorporateData, Officer


@dataclass
class EnrichedCompany:
    """Fully enriched company data."""

    # Input
    company_name: str
    input_jurisdiction: Optional[str] = None

    # Online presence
    websites: list[str] = field(default_factory=list)
    social_media: dict[str, str] = field(default_factory=dict)
    online_hit_count: int = 0
    has_wikipedia: bool = False
    has_news: bool = False
    regulatory_mentions: list[str] = field(default_factory=list)

    # Corporate data
    matched_name: Optional[str] = None
    company_number: Optional[str] = None
    jurisdiction: Optional[str] = None
    incorporation_date: Optional[str] = None
    dissolution_date: Optional[str] = None
    status: Optional[str] = None
    company_type: Optional[str] = None
    registered_address: Optional[str] = None
    officers: list[dict] = field(default_factory=list)
    officer_count: int = 0
    lifespan_days: Optional[int] = None
    previous_names: list[str] = field(default_factory=list)

    # Metadata
    enrichment_source: str = "unknown"
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame."""
        return asdict(self)

    def to_flat_dict(self) -> dict:
        """Convert to flattened dictionary for DataFrame display."""
        return {
            "company_name": self.company_name,
            "matched_name": self.matched_name or self.company_name,
            "jurisdiction": self.jurisdiction or self.input_jurisdiction,
            "status": self.status,
            "incorporation_date": self.incorporation_date,
            "lifespan_days": self.lifespan_days,
            "officer_count": self.officer_count,
            "online_hit_count": self.online_hit_count,
            "has_wikipedia": self.has_wikipedia,
            "has_news": self.has_news,
            "website_count": len(self.websites),
            "social_media_count": len(self.social_media),
            "regulatory_flags": len(self.regulatory_mentions),
            "registered_address": self.registered_address,
            "enrichment_source": self.enrichment_source,
        }


class EnrichmentPipeline:
    """Pipeline for enriching company data from multiple sources."""

    def __init__(
        self,
        brave_api_key: Optional[str] = None,
        opencorporates_token: Optional[str] = None,
        use_mocks: bool = True,
    ):
        """Initialize enrichment pipeline.

        Args:
            brave_api_key: Brave Search API key
            opencorporates_token: OpenCorporates API token
            use_mocks: Fall back to mock data if APIs unavailable
        """
        self.brave_client = BraveSearchClient(api_key=brave_api_key)
        self.oc_client = OpenCorporatesClient(api_token=opencorporates_token)
        self.use_mocks = use_mocks

    def _merge_online_presence(
        self,
        enriched: EnrichedCompany,
        presence: OnlinePresence,
    ) -> None:
        """Merge online presence data into enriched company."""
        enriched.websites = presence.websites
        enriched.social_media = presence.social_media
        enriched.online_hit_count = presence.hit_count
        enriched.has_wikipedia = presence.has_wikipedia
        enriched.has_news = presence.has_news
        enriched.regulatory_mentions = presence.regulatory_mentions

        if presence.error:
            enriched.errors.append(f"Brave Search: {presence.error}")

    def _merge_corporate_data(
        self,
        enriched: EnrichedCompany,
        corporate: CorporateData,
    ) -> None:
        """Merge corporate data into enriched company."""
        enriched.matched_name = corporate.name
        enriched.company_number = corporate.company_number
        enriched.jurisdiction = corporate.jurisdiction
        enriched.incorporation_date = corporate.incorporation_date
        enriched.dissolution_date = corporate.dissolution_date
        enriched.status = corporate.status
        enriched.company_type = corporate.company_type
        enriched.registered_address = corporate.registered_address
        enriched.lifespan_days = corporate.lifespan_days
        enriched.previous_names = corporate.previous_names

        # Convert officers to dicts
        enriched.officers = [
            {
                "name": o.name,
                "position": o.position,
                "start_date": o.start_date,
            }
            for o in corporate.officers
        ]
        enriched.officer_count = len(corporate.officers)

        if corporate.error:
            enriched.errors.append(f"OpenCorporates: {corporate.error}")

    def enrich_company(
        self,
        company_name: str,
        jurisdiction: Optional[str] = None,
    ) -> EnrichedCompany:
        """Enrich a single company with all available data.

        Args:
            company_name: Name of company to enrich
            jurisdiction: Optional jurisdiction code

        Returns:
            EnrichedCompany with all gathered data
        """
        enriched = EnrichedCompany(
            company_name=company_name,
            input_jurisdiction=jurisdiction,
        )

        sources_used = []

        # Get online presence
        if self.use_mocks:
            presence = self.brave_client.search_or_mock(company_name)
        else:
            presence = self.brave_client.search_company(company_name)

        self._merge_online_presence(enriched, presence)
        sources_used.append("brave" if self.brave_client.api_key else "brave_mock")

        # Get corporate data
        if self.use_mocks:
            results = self.oc_client.search_or_mock(company_name, jurisdiction)
        else:
            results = self.oc_client.search_companies(company_name, jurisdiction)

        if results:
            # Use the first (best) match
            best_match = results[0]
            self._merge_corporate_data(enriched, best_match)
            sources_used.append(
                "opencorporates" if self.oc_client.api_token else "opencorporates_mock"
            )

        enriched.enrichment_source = "+".join(sources_used)

        return enriched

    def enrich_companies(
        self,
        companies: list[dict],
        name_column: str = "Company Name",
        jurisdiction_column: Optional[str] = "Jurisdiction",
        progress_callback=None,
    ) -> list[EnrichedCompany]:
        """Enrich multiple companies.

        Args:
            companies: List of dicts with company info
            name_column: Column name for company name
            jurisdiction_column: Column name for jurisdiction (optional)
            progress_callback: Optional callback(current, total) for progress

        Returns:
            List of EnrichedCompany objects
        """
        results = []
        total = len(companies)

        for i, company in enumerate(companies):
            name = company.get(name_column, "")
            jurisdiction = company.get(jurisdiction_column) if jurisdiction_column else None

            if not name:
                continue

            enriched = self.enrich_company(name, jurisdiction)
            results.append(enriched)

            if progress_callback:
                progress_callback(i + 1, total)

        return results

    def enrich_to_dicts(
        self,
        companies: list[dict],
        name_column: str = "Company Name",
        jurisdiction_column: Optional[str] = "Jurisdiction",
        flatten: bool = True,
        progress_callback=None,
    ) -> list[dict]:
        """Enrich companies and return as list of dicts.

        Args:
            companies: List of dicts with company info
            name_column: Column name for company name
            jurisdiction_column: Column name for jurisdiction
            flatten: If True, return flattened dicts for DataFrame
            progress_callback: Optional callback for progress

        Returns:
            List of dicts with enriched data
        """
        enriched = self.enrich_companies(
            companies,
            name_column,
            jurisdiction_column,
            progress_callback,
        )

        if flatten:
            return [e.to_flat_dict() for e in enriched]
        return [e.to_dict() for e in enriched]
