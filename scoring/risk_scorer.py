"""Risk scoring engine for company legitimacy assessment.

Uses a weighted scoring framework on a 0-4 scale (GPA-like)
with categories and subfactors as specified in the project requirements.
"""

from dataclasses import dataclass, field
from typing import Optional

from config import HIGH_RISK_JURISDICTIONS, MEDIUM_RISK_JURISDICTIONS, SCORING_WEIGHTS


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of risk score."""

    # Category scores (0-4 scale)
    online_activity_score: float = 0.0
    corporate_info_score: float = 0.0
    officers_structure_score: float = 0.0
    jurisdiction_risk_score: float = 0.0
    external_factors_score: float = 0.0

    # Weighted total (0-4 scale)
    total_score: float = 0.0

    # Risk level
    risk_level: str = "Unknown"

    # Red flags
    flags: list[str] = field(default_factory=list)

    # Detailed subfactor scores
    subfactors: dict = field(default_factory=dict)


class RiskScorer:
    """Calculates risk scores for enriched company data."""

    # Scoring thresholds
    HIGH_RISK_THRESHOLD = 2.0
    MEDIUM_RISK_THRESHOLD = 3.0

    # Subfactor weights (3x for key factors, 1x for others)
    KEY_FACTOR_WEIGHT = 3
    NORMAL_FACTOR_WEIGHT = 1

    def __init__(self, weights: Optional[dict] = None):
        """Initialize scorer with optional custom weights.

        Args:
            weights: Custom category weights. Defaults to config.
        """
        self.weights = weights or SCORING_WEIGHTS

    def _score_online_activity(self, data: dict) -> tuple[float, dict, list[str]]:
        """Score online activity category (0-4 scale).

        Subfactors:
        - Hit count (3x weight): 4 if >5, 2 if 2-5, 0 if <2
        - Social links (1x weight): 4 if >=3, 2 if 1-2, 0 if 0
        - Website quality (1x weight): 4 if has wiki, 2 if has sites, 0 if none
        """
        subfactors = {}
        flags = []

        # Hit count (key factor - 3x)
        hit_count = data.get("online_hit_count", 0)
        if hit_count > 5:
            subfactors["hit_count"] = (4.0, self.KEY_FACTOR_WEIGHT)
        elif hit_count >= 2:
            subfactors["hit_count"] = (2.0, self.KEY_FACTOR_WEIGHT)
        else:
            subfactors["hit_count"] = (0.0, self.KEY_FACTOR_WEIGHT)
            flags.append("Low online presence")

        # Social links (1x)
        social_count = data.get("social_media_count", len(data.get("social_media", {})))
        if social_count >= 3:
            subfactors["social_links"] = (4.0, self.NORMAL_FACTOR_WEIGHT)
        elif social_count >= 1:
            subfactors["social_links"] = (2.0, self.NORMAL_FACTOR_WEIGHT)
        else:
            subfactors["social_links"] = (0.0, self.NORMAL_FACTOR_WEIGHT)
            flags.append("No social media presence")

        # Website/Wikipedia (1x)
        has_wiki = data.get("has_wikipedia", False)
        website_count = data.get("website_count", len(data.get("websites", [])))
        if has_wiki:
            subfactors["website_quality"] = (4.0, self.NORMAL_FACTOR_WEIGHT)
        elif website_count > 0:
            subfactors["website_quality"] = (2.0, self.NORMAL_FACTOR_WEIGHT)
        else:
            subfactors["website_quality"] = (0.0, self.NORMAL_FACTOR_WEIGHT)

        # Calculate weighted average
        total_weighted = sum(s * w for s, w in subfactors.values())
        total_weight = sum(w for _, w in subfactors.values())
        score = total_weighted / total_weight if total_weight > 0 else 0.0

        return score, subfactors, flags

    def _score_corporate_info(self, data: dict) -> tuple[float, dict, list[str]]:
        """Score corporate info category (0-4 scale).

        Subfactors:
        - Status/Lifespan (3x weight): Based on active status and age
        - Address legitimacy (1x weight): Based on registered address
        """
        subfactors = {}
        flags = []

        # Status (key factor - 3x)
        status = str(data.get("status", "")).lower()
        lifespan_days = data.get("lifespan_days")

        status_score = 0.0
        if "active" in status:
            status_score = 4.0
        elif "suspended" in status:
            status_score = 2.0
            flags.append("Company suspended")
        elif "inactive" in status or "dissolved" in status:
            status_score = 0.0
            flags.append("Company inactive/dissolved")
        else:
            status_score = 2.0  # Unknown status

        # Adjust for lifespan
        if lifespan_days is not None:
            lifespan_years = lifespan_days / 365
            if lifespan_years > 5:
                lifespan_modifier = 1.0
            elif lifespan_years >= 2:
                lifespan_modifier = 0.75
            elif lifespan_years >= 1:
                lifespan_modifier = 0.5
            else:
                lifespan_modifier = 0.25
                flags.append("Short company lifespan (<1 year)")

            status_score = status_score * lifespan_modifier

        subfactors["status_lifespan"] = (status_score, self.KEY_FACTOR_WEIGHT)

        # Address legitimacy (1x)
        address = data.get("registered_address")
        if address:
            # Simple heuristic: longer addresses tend to be more legitimate
            if len(address) > 30:
                subfactors["address_legitimacy"] = (4.0, self.NORMAL_FACTOR_WEIGHT)
            else:
                subfactors["address_legitimacy"] = (2.0, self.NORMAL_FACTOR_WEIGHT)
        else:
            subfactors["address_legitimacy"] = (0.0, self.NORMAL_FACTOR_WEIGHT)
            flags.append("No registered address")

        # Calculate weighted average
        total_weighted = sum(s * w for s, w in subfactors.values())
        total_weight = sum(w for _, w in subfactors.values())
        score = total_weighted / total_weight if total_weight > 0 else 0.0

        return score, subfactors, flags

    def _score_officers_structure(self, data: dict) -> tuple[float, dict, list[str]]:
        """Score officers & structure category (0-4 scale).

        Subfactors:
        - Officer count (3x weight): 4 if >3, 3 if 2-3, 2 if 1, 0 if 0
        - Address match (1x weight): Based on officer addresses
        """
        subfactors = {}
        flags = []

        # Officer count (key factor - 3x)
        officer_count = data.get("officer_count", len(data.get("officers", [])))
        if officer_count > 3:
            subfactors["officer_count"] = (4.0, self.KEY_FACTOR_WEIGHT)
        elif officer_count >= 2:
            subfactors["officer_count"] = (3.0, self.KEY_FACTOR_WEIGHT)
        elif officer_count == 1:
            subfactors["officer_count"] = (2.0, self.KEY_FACTOR_WEIGHT)
            flags.append("Single officer only")
        else:
            subfactors["officer_count"] = (0.0, self.KEY_FACTOR_WEIGHT)
            flags.append("No officers found")

        # Address match (1x) - placeholder for now
        # In full implementation, would compare officer addresses to company
        has_address = bool(data.get("registered_address"))
        has_officers = officer_count > 0
        if has_address and has_officers:
            subfactors["address_match"] = (3.0, self.NORMAL_FACTOR_WEIGHT)
        elif has_address or has_officers:
            subfactors["address_match"] = (1.5, self.NORMAL_FACTOR_WEIGHT)
        else:
            subfactors["address_match"] = (0.0, self.NORMAL_FACTOR_WEIGHT)

        # Calculate weighted average
        total_weighted = sum(s * w for s, w in subfactors.values())
        total_weight = sum(w for _, w in subfactors.values())
        score = total_weighted / total_weight if total_weight > 0 else 0.0

        return score, subfactors, flags

    def _score_jurisdiction_risk(self, data: dict) -> tuple[float, dict, list[str]]:
        """Score jurisdiction risk category (0-4 scale).

        Subfactors:
        - Jurisdiction risk level (3x weight): 0 for high-risk, 2 for medium, 4 for low
        - Other factors (1x weight): Placeholder for additional checks
        """
        subfactors = {}
        flags = []

        # Jurisdiction risk (key factor - 3x)
        jurisdiction = str(data.get("jurisdiction", "")).lower()

        if jurisdiction in HIGH_RISK_JURISDICTIONS:
            subfactors["jurisdiction_risk"] = (0.0, self.KEY_FACTOR_WEIGHT)
            flags.append(f"High-risk jurisdiction: {jurisdiction.upper()}")
        elif jurisdiction in MEDIUM_RISK_JURISDICTIONS:
            subfactors["jurisdiction_risk"] = (2.0, self.KEY_FACTOR_WEIGHT)
            flags.append(f"Medium-risk jurisdiction: {jurisdiction.upper()}")
        elif jurisdiction:
            subfactors["jurisdiction_risk"] = (4.0, self.KEY_FACTOR_WEIGHT)
        else:
            subfactors["jurisdiction_risk"] = (2.0, self.KEY_FACTOR_WEIGHT)
            flags.append("Unknown jurisdiction")

        # Other factors placeholder (1x)
        subfactors["other_factors"] = (2.0, self.NORMAL_FACTOR_WEIGHT)

        # Calculate weighted average
        total_weighted = sum(s * w for s, w in subfactors.values())
        total_weight = sum(w for _, w in subfactors.values())
        score = total_weighted / total_weight if total_weight > 0 else 0.0

        return score, subfactors, flags

    def _score_external_factors(self, data: dict) -> tuple[float, dict, list[str]]:
        """Score external factors category (0-4 scale).

        Subfactors:
        - Regulatory mentions (3x weight): Lower if fraud/SEC mentions found
        - Data confidence (1x weight): Based on completeness of data
        """
        subfactors = {}
        flags = []

        # Regulatory mentions (key factor - 3x)
        reg_flags = data.get("regulatory_flags", len(data.get("regulatory_mentions", [])))
        if reg_flags == 0:
            subfactors["regulatory"] = (4.0, self.KEY_FACTOR_WEIGHT)
        elif reg_flags <= 2:
            subfactors["regulatory"] = (2.0, self.KEY_FACTOR_WEIGHT)
            flags.append("Regulatory mentions found")
        else:
            subfactors["regulatory"] = (0.0, self.KEY_FACTOR_WEIGHT)
            flags.append("Multiple regulatory flags")

        # Data confidence (1x)
        # Count how many key fields are filled
        key_fields = [
            "status",
            "incorporation_date",
            "jurisdiction",
            "registered_address",
            "officer_count",
        ]
        filled = sum(1 for f in key_fields if data.get(f))
        confidence = (filled / len(key_fields)) * 4.0
        subfactors["confidence"] = (confidence, self.NORMAL_FACTOR_WEIGHT)

        if confidence < 2.0:
            flags.append("Low data confidence")

        # Calculate weighted average
        total_weighted = sum(s * w for s, w in subfactors.values())
        total_weight = sum(w for _, w in subfactors.values())
        score = total_weighted / total_weight if total_weight > 0 else 0.0

        return score, subfactors, flags

    def calculate_score(self, data: dict) -> ScoreBreakdown:
        """Calculate comprehensive risk score for company data.

        Args:
            data: Dictionary with enriched company data

        Returns:
            ScoreBreakdown with detailed scoring information
        """
        breakdown = ScoreBreakdown()
        all_subfactors = {}
        all_flags = []

        # Score each category
        online_score, online_sub, online_flags = self._score_online_activity(data)
        breakdown.online_activity_score = online_score
        all_subfactors["online_activity"] = online_sub
        all_flags.extend(online_flags)

        corp_score, corp_sub, corp_flags = self._score_corporate_info(data)
        breakdown.corporate_info_score = corp_score
        all_subfactors["corporate_info"] = corp_sub
        all_flags.extend(corp_flags)

        officers_score, officers_sub, officers_flags = self._score_officers_structure(data)
        breakdown.officers_structure_score = officers_score
        all_subfactors["officers_structure"] = officers_sub
        all_flags.extend(officers_flags)

        jur_score, jur_sub, jur_flags = self._score_jurisdiction_risk(data)
        breakdown.jurisdiction_risk_score = jur_score
        all_subfactors["jurisdiction_risk"] = jur_sub
        all_flags.extend(jur_flags)

        ext_score, ext_sub, ext_flags = self._score_external_factors(data)
        breakdown.external_factors_score = ext_score
        all_subfactors["external_factors"] = ext_sub
        all_flags.extend(ext_flags)

        # Calculate weighted total
        breakdown.total_score = (
            online_score * self.weights["online_activity"]
            + corp_score * self.weights["corporate_info"]
            + officers_score * self.weights["officers_structure"]
            + jur_score * self.weights["jurisdiction_risk"]
            + ext_score * self.weights["external_factors"]
        )

        # Clamp to 0-4
        breakdown.total_score = max(0.0, min(4.0, breakdown.total_score))

        # Determine risk level
        if breakdown.total_score >= self.MEDIUM_RISK_THRESHOLD:
            breakdown.risk_level = "Low Risk"
        elif breakdown.total_score >= self.HIGH_RISK_THRESHOLD:
            breakdown.risk_level = "Medium Risk"
        else:
            breakdown.risk_level = "High Risk"

        # Deduplicate flags
        breakdown.flags = list(dict.fromkeys(all_flags))
        breakdown.subfactors = all_subfactors

        return breakdown

    def score_companies(self, companies: list[dict]) -> list[dict]:
        """Score multiple companies and return enriched data with scores.

        Args:
            companies: List of enriched company dicts

        Returns:
            List of dicts with added scoring fields
        """
        results = []

        for company in companies:
            breakdown = self.calculate_score(company)

            scored = company.copy()
            scored["risk_score"] = round(breakdown.total_score, 2)
            scored["risk_level"] = breakdown.risk_level
            scored["risk_flags"] = breakdown.flags
            scored["online_activity_score"] = round(breakdown.online_activity_score, 2)
            scored["corporate_info_score"] = round(breakdown.corporate_info_score, 2)
            scored["officers_structure_score"] = round(breakdown.officers_structure_score, 2)
            scored["jurisdiction_risk_score"] = round(breakdown.jurisdiction_risk_score, 2)
            scored["external_factors_score"] = round(breakdown.external_factors_score, 2)

            results.append(scored)

        return results
