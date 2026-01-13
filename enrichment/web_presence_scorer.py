"""Web Presence Scoring from Brave Search API.

This module analyzes Brave Search API responses to calculate a web presence
score indicating how likely a company is legitimate vs a shell company.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WebPresenceScore:
    """Detailed web presence scoring results."""

    # Overall score (0-4 scale, higher = more legitimate)
    score: float = 0.0
    confidence: float = 0.0  # 0-1, how confident we are in the score

    # Signal counts
    total_results: int = 0
    relevant_results: int = 0

    # Platform presence
    has_linkedin: bool = False
    has_wikipedia: bool = False
    has_twitter: bool = False
    has_facebook: bool = False
    has_github: bool = False
    has_official_website: bool = False

    # Business legitimacy signals
    has_news_coverage: bool = False
    has_business_database: bool = False  # Crunchbase, PitchBook, etc.
    has_financial_coverage: bool = False  # Bloomberg, Reuters

    # Risk signals
    has_regulatory_mentions: bool = False
    has_fraud_keywords: bool = False
    has_lawsuit_mentions: bool = False

    # Detailed findings
    official_website_url: Optional[str] = None
    social_profiles: dict = field(default_factory=dict)
    news_sources: list = field(default_factory=list)
    regulatory_mentions: list = field(default_factory=list)
    red_flags: list = field(default_factory=list)
    domains_found: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'score': self.score,
            'confidence': self.confidence,
            'total_results': self.total_results,
            'relevant_results': self.relevant_results,
            'has_linkedin': self.has_linkedin,
            'has_wikipedia': self.has_wikipedia,
            'has_twitter': self.has_twitter,
            'has_facebook': self.has_facebook,
            'has_github': self.has_github,
            'has_official_website': self.has_official_website,
            'has_news_coverage': self.has_news_coverage,
            'has_business_database': self.has_business_database,
            'has_financial_coverage': self.has_financial_coverage,
            'has_regulatory_mentions': self.has_regulatory_mentions,
            'has_fraud_keywords': self.has_fraud_keywords,
            'has_lawsuit_mentions': self.has_lawsuit_mentions,
            'official_website_url': self.official_website_url,
            'social_profiles': self.social_profiles,
            'news_sources': self.news_sources,
            'regulatory_mentions': self.regulatory_mentions,
            'red_flags': self.red_flags,
            'domains_found': self.domains_found,
        }


class WebPresenceScorer:
    """Analyze Brave Search API responses to score company web presence."""

    # Domain categories
    SOCIAL_DOMAINS = {
        'linkedin.com': 'linkedin',
        'twitter.com': 'twitter',
        'x.com': 'twitter',
        'facebook.com': 'facebook',
        'instagram.com': 'instagram',
        'github.com': 'github',
        'youtube.com': 'youtube',
    }

    NEWS_DOMAINS = {
        'reuters.com': 'Reuters',
        'bloomberg.com': 'Bloomberg',
        'cnbc.com': 'CNBC',
        'wsj.com': 'Wall Street Journal',
        'nytimes.com': 'New York Times',
        'ft.com': 'Financial Times',
        'forbes.com': 'Forbes',
        'businessinsider.com': 'Business Insider',
    }

    BUSINESS_DATABASES = {
        'crunchbase.com': 'Crunchbase',
        'pitchbook.com': 'PitchBook',
        'golden.com': 'Golden',
        'rocketreach.co': 'RocketReach',
        'zoominfo.com': 'ZoomInfo',
        'dnb.com': 'Dun & Bradstreet',
        'opencorporates.com': 'OpenCorporates',
    }

    REGULATORY_DOMAINS = {
        'sec.gov': 'SEC',
        'justice.gov': 'DOJ',
        'treasury.gov': 'Treasury',
        'ftc.gov': 'FTC',
        'fbi.gov': 'FBI',
        'finra.org': 'FINRA',
    }

    FRAUD_KEYWORDS = [
        'fraud', 'scam', 'ponzi', 'pyramid', 'scheme',
        'charged', 'indicted', 'convicted', 'settlement',
        'enforcement', 'violation', 'penalty', 'fine',
        'money laundering', 'wire fraud', 'securities fraud',
        'lawsuit', 'litigation', 'bankruptcy',
    ]

    # Scoring weights
    WEIGHTS = {
        'linkedin': 0.8,
        'wikipedia': 1.0,
        'twitter': 0.4,
        'facebook': 0.3,
        'github': 0.3,
        'official_website': 0.8,
        'news_coverage': 0.6,
        'business_database': 0.5,
        'financial_news': 0.7,
        'high_result_count': 0.5,  # 10+ results
        'regulatory_mention': -0.3,  # Negative but not always bad
        'fraud_keyword': -0.8,
        'lawsuit_mention': -0.5,
        'no_social': -0.5,
        'low_results': -1.0,  # < 3 results
        'irrelevant_results': -0.5,  # Results don't match company
    }

    def __init__(self):
        """Initialize the scorer."""
        pass

    def score_response(self, brave_response: dict, company_name: str) -> WebPresenceScore:
        """Score a Brave Search API response for web presence signals.

        Args:
            brave_response: Raw JSON response from Brave Search API
            company_name: The company name that was searched

        Returns:
            WebPresenceScore with detailed scoring results
        """
        result = WebPresenceScore()

        # Get web results
        web_data = brave_response.get('web', {})
        results = web_data.get('results', [])

        result.total_results = len(results)

        if not results:
            result.score = 0.5  # Very low score for no results
            result.confidence = 0.8
            result.red_flags.append('No search results found')
            return result

        # Analyze each result
        company_words = self._normalize_company_name(company_name)

        for res in results:
            self._analyze_result(res, company_words, result)

        # Calculate final score
        result.score = self._calculate_score(result, company_words)
        result.confidence = self._calculate_confidence(result)

        return result

    def _normalize_company_name(self, name: str) -> set:
        """Extract significant words from company name for matching."""
        # Remove common suffixes and entity type indicators
        suffixes = [
            # English
            'inc', 'llc', 'ltd', 'corp', 'corporation', 'company',
            'co', 'pte', 'pvt', 'plc', 'limited', 'the',
            # German
            'gmbh', 'ag', 'kg',
            # Russian
            'ooo', 'oao', 'zao', 'pao',  # Russian entity types
            # French/Spanish
            'sa', 'sarl', 'sas',
            # Other
            'bv', 'nv', 'ab', 'oy',
            # Generic
            'holdings', 'group', 'international', 'global', 'enterprises'
        ]

        words = re.findall(r'\b\w+\b', name.lower())
        words = [w for w in words if w not in suffixes and len(w) > 2]

        return set(words)

    def _analyze_result(self, result: dict, company_words: set, score: WebPresenceScore):
        """Analyze a single search result and update scoring signals."""
        url = result.get('url', '').lower()
        title = result.get('title', '').lower()
        description = result.get('description', '').lower()
        netloc = result.get('meta_url', {}).get('netloc', '').lower()

        # Track domain
        if netloc and netloc not in score.domains_found:
            score.domains_found.append(netloc)

        # Check relevance - require majority of significant words to match
        content = f"{title} {description} {url}"
        matching_words = sum(1 for word in company_words if word in content)
        # Consider relevant if at least 50% of company name words match
        is_relevant = matching_words >= max(1, len(company_words) * 0.5) if company_words else False

        # Skip analysis if result is not relevant to the company
        if not is_relevant:
            # Still count it but don't add positive signals from irrelevant results
            return

        # Count relevant result
        score.relevant_results += 1

        # Social media presence
        for domain, platform in self.SOCIAL_DOMAINS.items():
            if domain in url:
                if platform == 'linkedin':
                    score.has_linkedin = True
                    score.social_profiles['linkedin'] = result.get('url')
                elif platform == 'twitter':
                    score.has_twitter = True
                    score.social_profiles['twitter'] = result.get('url')
                elif platform == 'facebook':
                    score.has_facebook = True
                    score.social_profiles['facebook'] = result.get('url')
                elif platform == 'github':
                    score.has_github = True
                    score.social_profiles['github'] = result.get('url')
                break

        # Wikipedia
        if 'wikipedia.org' in url:
            score.has_wikipedia = True

        # News coverage
        for domain, source in self.NEWS_DOMAINS.items():
            if domain in url:
                score.has_news_coverage = True
                if domain in ['bloomberg.com', 'reuters.com', 'ft.com']:
                    score.has_financial_coverage = True
                if source not in score.news_sources:
                    score.news_sources.append(source)
                break

        # Business databases
        for domain, db_name in self.BUSINESS_DATABASES.items():
            if domain in url:
                score.has_business_database = True
                break

        # Official website detection
        if not score.has_official_website and is_relevant:
            # Check if this looks like an official company site
            is_social = any(d in url for d in self.SOCIAL_DOMAINS.keys())
            is_news = any(d in url for d in self.NEWS_DOMAINS.keys())
            is_db = any(d in url for d in self.BUSINESS_DATABASES.keys())
            is_reference = 'wikipedia.org' in url

            if not (is_social or is_news or is_db or is_reference):
                # Likely a company website
                if any(word in url for word in company_words):
                    score.has_official_website = True
                    score.official_website_url = result.get('url')

        # Regulatory mentions
        for domain, agency in self.REGULATORY_DOMAINS.items():
            if domain in url:
                score.has_regulatory_mentions = True
                mention = f"{agency}: {result.get('title', '')[:50]}"
                if mention not in score.regulatory_mentions:
                    score.regulatory_mentions.append(mention)
                break

        # Fraud keywords
        for keyword in self.FRAUD_KEYWORDS:
            if keyword in description:
                score.has_fraud_keywords = True
                if keyword not in score.red_flags:
                    score.red_flags.append(f'Found keyword: {keyword}')
                break

        # Lawsuit mentions
        lawsuit_terms = ['lawsuit', 'litigation', 'sued', 'court case', 'legal action']
        if any(term in description for term in lawsuit_terms):
            score.has_lawsuit_mentions = True

    def _calculate_score(self, result: WebPresenceScore, company_words: set) -> float:
        """Calculate final web presence score (0-4 scale)."""
        # Start with baseline
        score = 2.0

        # Positive signals
        if result.has_linkedin:
            score += self.WEIGHTS['linkedin']
        if result.has_wikipedia:
            score += self.WEIGHTS['wikipedia']
        if result.has_twitter:
            score += self.WEIGHTS['twitter']
        if result.has_facebook:
            score += self.WEIGHTS['facebook']
        if result.has_github:
            score += self.WEIGHTS['github']
        if result.has_official_website:
            score += self.WEIGHTS['official_website']
        if result.has_news_coverage:
            score += self.WEIGHTS['news_coverage']
        if result.has_business_database:
            score += self.WEIGHTS['business_database']
        if result.has_financial_coverage:
            score += self.WEIGHTS['financial_news']
        if result.total_results >= 10:
            score += self.WEIGHTS['high_result_count']

        # Negative signals
        if result.has_regulatory_mentions:
            score += self.WEIGHTS['regulatory_mention']
        if result.has_fraud_keywords:
            score += self.WEIGHTS['fraud_keyword']
        if result.has_lawsuit_mentions:
            score += self.WEIGHTS['lawsuit_mention']

        # No social media presence
        if not (result.has_linkedin or result.has_twitter or result.has_facebook):
            score += self.WEIGHTS['no_social']

        # Low result count
        if result.total_results < 3:
            score += self.WEIGHTS['low_results']

        # No relevant results - very suspicious
        if result.relevant_results == 0:
            score -= 2.0  # Major penalty
            result.red_flags.append('No relevant search results found - possible shell company')

        # Low relevance
        elif result.total_results > 0:
            relevance_ratio = result.relevant_results / result.total_results
            if relevance_ratio < 0.3:
                score += self.WEIGHTS['irrelevant_results']
                result.red_flags.append(f'Low relevance: {relevance_ratio:.0%} of results match')

        # Clamp to 0-4 range
        return max(0.0, min(4.0, score))

    def _calculate_confidence(self, result: WebPresenceScore) -> float:
        """Calculate confidence in the score (0-1)."""
        # More results = higher confidence
        if result.total_results >= 15:
            base_confidence = 0.9
        elif result.total_results >= 10:
            base_confidence = 0.8
        elif result.total_results >= 5:
            base_confidence = 0.7
        elif result.total_results >= 3:
            base_confidence = 0.6
        else:
            base_confidence = 0.4

        # Higher relevance = higher confidence
        if result.total_results > 0:
            relevance_factor = result.relevant_results / result.total_results
            base_confidence *= (0.5 + 0.5 * relevance_factor)

        return min(1.0, base_confidence)


def score_brave_response(brave_response: dict, company_name: str) -> dict:
    """Convenience function to score a Brave API response.

    Args:
        brave_response: Raw JSON from Brave Search API
        company_name: Company name that was searched

    Returns:
        Dictionary with scoring results
    """
    scorer = WebPresenceScorer()
    result = scorer.score_response(brave_response, company_name)
    return result.to_dict()


if __name__ == '__main__':
    import json

    # Test with saved responses
    print("=" * 60)
    print("Web Presence Scoring Test")
    print("=" * 60)

    scorer = WebPresenceScorer()

    # Test 1: Terraform Labs (known company)
    print("\n--- Test 1: Terraform Labs (known fraud case) ---")
    try:
        with open('data/brave_api_response_example.json', encoding='utf-8') as f:
            terraform_response = json.load(f)

        result = scorer.score_response(terraform_response, 'Terraform Labs')
        print(f"Score: {result.score:.2f}/4.0")
        print(f"Confidence: {result.confidence:.0%}")
        print(f"Total results: {result.total_results}")
        print(f"Relevant results: {result.relevant_results}")
        print(f"LinkedIn: {result.has_linkedin}")
        print(f"Wikipedia: {result.has_wikipedia}")
        print(f"News coverage: {result.has_news_coverage}")
        print(f"Regulatory mentions: {result.has_regulatory_mentions}")
        print(f"Red flags: {result.red_flags}")
    except FileNotFoundError:
        print("  Response file not found")

    # Test 2: Shell company
    print("\n--- Test 2: OOO Khartiya (OFAC sanctioned) ---")
    try:
        with open('data/brave_api_response_shell_company.json', encoding='utf-8') as f:
            shell_response = json.load(f)

        result = scorer.score_response(shell_response, 'OOO Khartiya')
        print(f"Score: {result.score:.2f}/4.0")
        print(f"Confidence: {result.confidence:.0%}")
        print(f"Total results: {result.total_results}")
        print(f"Relevant results: {result.relevant_results}")
        print(f"LinkedIn: {result.has_linkedin}")
        print(f"Wikipedia: {result.has_wikipedia}")
        print(f"News coverage: {result.has_news_coverage}")
        print(f"Red flags: {result.red_flags}")
    except FileNotFoundError:
        print("  Response file not found")
