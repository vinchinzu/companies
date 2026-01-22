"""
Risk scoring engine module.
Aggregates findings from all modules and calculates risk score.
"""

from typing import Dict, Any, List


class RiskScorer:
    """Calculate risk score based on verification results."""

    # Risk score thresholds
    LOW_RISK_THRESHOLD = 70
    MEDIUM_RISK_THRESHOLD = 40

    # Scoring weights
    REGISTRY_WEIGHT = 25
    SANCTIONS_WEIGHT = 50
    OFFSHORE_WEIGHT = 20
    TRADE_WEIGHT = 15

    def calculate_score(
        self,
        registry_result: Dict[str, Any],
        sanctions_result: Dict[str, Any],
        offshore_result: Dict[str, Any],
        trade_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate overall risk score.

        Args:
            registry_result: Results from registry checker
            sanctions_result: Results from sanctions checker
            offshore_result: Results from offshore checker
            trade_result: Results from trade checker

        Returns:
            Risk assessment with score and recommendations
        """
        # Start with neutral score
        base_score = 50
        score = base_score

        # Track adjustments for transparency
        adjustments = []
        critical_flags = []
        all_red_flags = []

        # Registry scoring
        registry_adjustment = self._score_registry(registry_result)
        score += registry_adjustment['points']
        adjustments.append(registry_adjustment)
        all_red_flags.extend(registry_result.get('red_flags', []))
        if registry_adjustment.get('critical'):
            critical_flags.extend(registry_adjustment.get('critical', []))

        # Sanctions scoring (most critical)
        sanctions_adjustment = self._score_sanctions(sanctions_result)
        score += sanctions_adjustment['points']
        adjustments.append(sanctions_adjustment)
        all_red_flags.extend(sanctions_result.get('red_flags', []))
        if sanctions_adjustment.get('critical'):
            critical_flags.extend(sanctions_adjustment.get('critical', []))

        # Offshore scoring
        offshore_adjustment = self._score_offshore(offshore_result)
        score += offshore_adjustment['points']
        adjustments.append(offshore_adjustment)
        all_red_flags.extend(offshore_result.get('red_flags', []))

        # Trade scoring
        trade_adjustment = self._score_trade(trade_result)
        score += trade_adjustment['points']
        adjustments.append(trade_adjustment)
        all_red_flags.extend(trade_result.get('red_flags', []))

        # Normalize score to 0-100
        final_score = max(0, min(100, score))

        # Determine risk level
        if final_score >= self.LOW_RISK_THRESHOLD:
            risk_level = 'LOW'
        elif final_score >= self.MEDIUM_RISK_THRESHOLD:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'HIGH'

        # Calculate overall confidence
        confidences = [
            registry_result.get('confidence', 0.0),
            sanctions_result.get('confidence', 0.0),
            offshore_result.get('confidence', 0.0),
            trade_result.get('confidence', 0.0)
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Generate recommendations
        recommendations = self._generate_recommendations(
            risk_level,
            critical_flags,
            registry_result,
            sanctions_result,
            offshore_result,
            trade_result
        )

        return {
            'risk_score': int(final_score),
            'risk_level': risk_level,
            'confidence': round(avg_confidence, 2),
            'adjustments': adjustments,
            'critical_flags': critical_flags,
            'all_red_flags': all_red_flags,
            'recommendations': recommendations
        }

    def _score_registry(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Score registry results."""
        points = 0
        critical = []
        details = []

        if not result.get('found'):
            points -= 20
            critical.append('Company not found in registry')
            details.append('Not found: -20 points')
        else:
            status = result.get('status', '')

            if status == 'active':
                points += 15
                details.append('Active status: +15 points')

                # Bonus for recent filings
                if result.get('recent_filings', 0) > 0 or result.get('recent_10q_date'):
                    points += 5
                    details.append('Recent filings: +5 points')

                # Bonus for officers
                if result.get('officers_count', 0) > 0:
                    points += 5
                    details.append('Officers listed: +5 points')

            elif status in ['dissolved', 'struck_off']:
                points -= 15
                critical.append('Company dissolved or struck off')
                details.append('Dissolved/struck off: -15 points')

        return {
            'category': 'Registry',
            'points': points,
            'details': details,
            'critical': critical
        }

    def _score_sanctions(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Score sanctions results (most impactful)."""
        points = 0
        critical = []
        details = []

        sanctions_hits = result.get('sanctions_hits', 0)
        pep_hits = result.get('pep_hits', 0)

        if sanctions_hits > 0:
            points -= 30
            critical.append(f'Sanctions match found ({sanctions_hits} hit(s))')
            details.append(f'Sanctions hits: -{30} points')

        if pep_hits > 0:
            points -= 10
            critical.append(f'PEP involvement ({pep_hits} hit(s))')
            details.append(f'PEP hits: -{10} points')

        if sanctions_hits == 0 and pep_hits == 0 and result.get('confidence', 0) > 0.5:
            points += 10
            details.append('Clean sanctions check: +10 points')

        return {
            'category': 'Sanctions',
            'points': points,
            'details': details,
            'critical': critical
        }

    def _score_offshore(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Score offshore entity results."""
        points = 0
        critical = []
        details = []

        offshore_hits = result.get('offshore_hits', 0)

        if offshore_hits > 0:
            points -= 15
            critical.append(f'Found in offshore leaks ({offshore_hits} hit(s))')
            details.append(f'Offshore hits: -{15} points')

            # Additional penalty for tax havens
            jurisdictions = result.get('jurisdictions', [])
            for jurisdiction in jurisdictions:
                from utils.helpers import is_tax_haven
                if is_tax_haven(jurisdiction):
                    points -= 5
                    details.append(f'Tax haven jurisdiction ({jurisdiction}): -{5} points')
                    break

        return {
            'category': 'Offshore',
            'points': points,
            'details': details,
            'critical': critical
        }

    def _score_trade(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Score trade activity results."""
        points = 0
        details = []

        if result.get('has_trade_data'):
            if result.get('industry_aligned'):
                points += 10
                details.append('Industry trade alignment: +10 points')
            elif result.get('country_trade_volume', 0) == 0:
                points -= 10
                details.append('No country trade in sector: -10 points')

        # Note: Limited impact since company-level data not available
        details.append('Note: Country-level data only, manual verification needed')

        return {
            'category': 'Trade',
            'points': points,
            'details': details,
            'critical': []
        }

    def _generate_recommendations(
        self,
        risk_level: str,
        critical_flags: List[str],
        registry_result: Dict,
        sanctions_result: Dict,
        offshore_result: Dict,
        trade_result: Dict
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if risk_level == 'HIGH':
            recommendations.append('IMMEDIATE ACTION: High shell company risk detected')

            if critical_flags:
                recommendations.append('Critical issues require investigation:')
                for flag in critical_flags:
                    recommendations.append(f'  - {flag}')

            recommendations.append('Recommended next steps:')
            recommendations.append('  1. Verify beneficial ownership')
            recommendations.append('  2. Request business documentation')
            recommendations.append('  3. Check for actual business operations')
            recommendations.append('  4. Consider enhanced due diligence')

        elif risk_level == 'MEDIUM':
            recommendations.append('CAUTION: Some shell company indicators detected')
            recommendations.append('Recommended actions:')
            recommendations.append('  1. Review red flags listed above')
            recommendations.append('  2. Verify recent business activity')
            recommendations.append('  3. Check ImportYeti for trade records')

        else:  # LOW
            recommendations.append('LOW RISK: Company appears legitimate')
            recommendations.append('Standard due diligence recommended')

        # Specific recommendations based on findings
        if not registry_result.get('found'):
            recommendations.append('ACTION: Verify company name and jurisdiction')

        if sanctions_result.get('sanctions_hits', 0) > 0:
            recommendations.append('ALERT: Sanctions match requires immediate review')

        if offshore_result.get('offshore_hits', 0) > 0:
            recommendations.append('INVESTIGATE: Offshore entity connections found')

        if trade_result.get('manual_check_needed'):
            url = trade_result.get('importyeti_url', '')
            recommendations.append(f'VERIFY TRADE: Check ImportYeti manually: {url}')

        return recommendations
