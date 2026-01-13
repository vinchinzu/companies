"""Brave Search API integration for online presence detection."""

import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from config import BRAVE_API_KEY, BRAVE_SEARCH_URL, RATE_LIMIT_DELAY


@dataclass
class OnlinePresence:
    """Company online presence data."""

    websites: list[str] = field(default_factory=list)
    social_media: dict[str, str] = field(default_factory=dict)
    hit_count: int = 0
    snippets: list[str] = field(default_factory=list)
    has_wikipedia: bool = False
    has_news: bool = False
    regulatory_mentions: list[str] = field(default_factory=list)
    error: Optional[str] = None


class BraveSearchClient:
    """Client for Brave Search API."""

    SOCIAL_DOMAINS = {
        "linkedin.com": "linkedin",
        "facebook.com": "facebook",
        "twitter.com": "twitter",
        "x.com": "twitter",
        "youtube.com": "youtube",
        "instagram.com": "instagram",
        "tiktok.com": "tiktok",
        "github.com": "github",
    }

    REGULATORY_KEYWORDS = [
        "sec.gov",
        "justice.gov",
        "fraud",
        "investigation",
        "enforcement",
        "penalty",
        "settlement",
        "charged",
        "lawsuit",
        "violation",
        "ponzi",
        "scam",
    ]

    def __init__(self, api_key: Optional[str] = None, delay: float = None):
        """Initialize Brave Search client.

        Args:
            api_key: Brave API key. Defaults to config value.
            delay: Delay between requests in seconds.
        """
        self.api_key = api_key or BRAVE_API_KEY
        self.delay = delay if delay is not None else RATE_LIMIT_DELAY
        self.session = requests.Session()

    def _make_request(self, query: str, count: int = 20) -> Optional[dict]:
        """Make API request to Brave Search."""
        if not self.api_key:
            return {"error": "No API key configured"}

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }

        params = {
            "q": query,
            "count": count,
            "text_decorations": False,
            "safesearch": "off",
        }

        try:
            response = self.session.get(
                BRAVE_SEARCH_URL,
                headers=headers,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            time.sleep(self.delay)
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def _extract_social_links(self, results: list[dict]) -> dict[str, str]:
        """Extract social media links from search results."""
        social = {}

        for result in results:
            url = result.get("url", "").lower()
            for domain, platform in self.SOCIAL_DOMAINS.items():
                if domain in url and platform not in social:
                    social[platform] = result.get("url", "")
                    break

        return social

    def _extract_websites(self, results: list[dict], company_name: str) -> list[str]:
        """Extract potential official websites."""
        websites = []
        company_words = company_name.lower().split()

        for result in results:
            url = result.get("url", "")
            title = result.get("title", "").lower()

            # Skip social media
            is_social = any(
                domain in url.lower() for domain in self.SOCIAL_DOMAINS.keys()
            )
            if is_social:
                continue

            # Check if likely official
            is_official = (
                "official" in title
                or any(word in url.lower() for word in company_words if len(word) > 3)
            )

            if is_official:
                websites.append(url)

        return websites[:5]

    def _check_regulatory_mentions(
        self, results: list[dict]
    ) -> tuple[list[str], bool]:
        """Check for regulatory/fraud mentions in results."""
        mentions = []
        has_news = False

        for result in results:
            url = result.get("url", "").lower()
            title = result.get("title", "").lower()
            description = result.get("description", "").lower()
            content = f"{title} {description}"

            # Check for news
            if any(
                news in url
                for news in ["news", "reuters", "bloomberg", "wsj", "nytimes"]
            ):
                has_news = True

            # Check for regulatory mentions
            for keyword in self.REGULATORY_KEYWORDS:
                if keyword in content or keyword in url:
                    mentions.append(f"{keyword}: {result.get('title', '')[:50]}")
                    break

        return mentions[:5], has_news

    def search_company(self, company_name: str) -> OnlinePresence:
        """Search for company online presence.

        Args:
            company_name: Name of company to search

        Returns:
            OnlinePresence dataclass with results
        """
        presence = OnlinePresence()

        query = f"{company_name} official website company"
        data = self._make_request(query)

        if "error" in data:
            presence.error = data["error"]
            return presence

        results = data.get("web", {}).get("results", [])
        presence.hit_count = len(results)

        if not results:
            return presence

        presence.websites = self._extract_websites(results, company_name)
        presence.social_media = self._extract_social_links(results)
        presence.snippets = [
            r.get("description", "")[:200] for r in results[:3] if r.get("description")
        ]
        presence.has_wikipedia = any(
            "wikipedia.org" in r.get("url", "").lower() for r in results
        )
        presence.regulatory_mentions, presence.has_news = self._check_regulatory_mentions(
            results
        )

        return presence

    def search_company_news(self, company_name: str) -> OnlinePresence:
        """Search specifically for company news and regulatory mentions."""
        presence = OnlinePresence()

        query = f"{company_name} news SEC fraud investigation"
        data = self._make_request(query, count=10)

        if "error" in data:
            presence.error = data["error"]
            return presence

        results = data.get("web", {}).get("results", [])
        presence.hit_count = len(results)
        presence.regulatory_mentions, presence.has_news = self._check_regulatory_mentions(
            results
        )
        presence.snippets = [
            r.get("description", "")[:200] for r in results[:3] if r.get("description")
        ]

        return presence

    def get_mock_presence(self, company_name: str) -> OnlinePresence:
        """Return mock data when no API key is available (for demo)."""
        import random

        # Simulate different profiles
        is_legitimate = random.random() > 0.3

        if is_legitimate:
            return OnlinePresence(
                websites=[f"https://www.{company_name.lower().replace(' ', '')}.com"],
                social_media={
                    "linkedin": f"https://linkedin.com/company/{company_name.lower().replace(' ', '-')}",
                    "twitter": f"https://twitter.com/{company_name.lower().replace(' ', '')}",
                },
                hit_count=random.randint(50, 200),
                snippets=[f"{company_name} is a leading company..."],
                has_wikipedia=random.random() > 0.5,
                has_news=True,
                regulatory_mentions=[],
            )
        else:
            return OnlinePresence(
                websites=[],
                social_media={},
                hit_count=random.randint(0, 5),
                snippets=[],
                has_wikipedia=False,
                has_news=False,
                regulatory_mentions=["SEC investigation mentioned"]
                if random.random() > 0.7
                else [],
            )

    def search_or_mock(self, company_name: str) -> OnlinePresence:
        """Search for company, falling back to mock data if no API key."""
        if self.api_key:
            return self.search_company(company_name)
        return self.get_mock_presence(company_name)
