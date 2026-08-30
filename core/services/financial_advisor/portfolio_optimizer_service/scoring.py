"""Scoring, health-label, diversification-rating, and explanation helpers.

NOTE (200-line file convention): part of the split of
core/services/financial_advisor/portfolio_optimizer_service.py (659 lines).
`_health_label_key`, `_diversification_rating`, and `_health_explanation_key`
intentionally duplicate the equivalent module-level functions in
calculations.py (that duplication predates this split and is preserved
as-is); this file moves the original service methods verbatim.
"""
from __future__ import annotations

from typing import Dict


class ScoringMixin:
    def _score_range_metric(self, value_pct: float, low: float, high: float) -> float:
        from .calculations import score_range_metric
        return score_range_metric(value_pct, low, high)

    def _emergency_fund_months(self, liquid_value: float, monthly_expenses: float) -> float:
        from .calculations import emergency_fund_months
        return emergency_fund_months(liquid_value, monthly_expenses)

    def _score_emergency_fund(self, months: float) -> float:
        from .calculations import score_emergency_fund
        return score_emergency_fund(months)

    def _score_diversification(self, percentages: Dict[str, float]) -> float:
        from .calculations import score_diversification
        return score_diversification(percentages)

    def _health_label_key(self, score: float) -> str:
        if score >= 90:
            return "portfolio_optimizer_health_excellent"
        if score >= 75:
            return "portfolio_optimizer_health_good"
        if score >= 60:
            return "portfolio_optimizer_health_average"
        return "portfolio_optimizer_health_attention"

    def _diversification_rating(self, *, asset_classes_owned: int, largest_concentration_pct: float, liquid_pct: float, diversification_metric: float) -> str:
        score = 0
        if asset_classes_owned >= 4:
            score += 3
        elif asset_classes_owned == 3:
            score += 2
        elif asset_classes_owned == 2:
            score += 1

        if largest_concentration_pct <= 35:
            score += 3
        elif largest_concentration_pct <= 50:
            score += 2
        elif largest_concentration_pct <= 65:
            score += 1

        if 15 <= liquid_pct <= 35:
            score += 2
        elif 10 <= liquid_pct <= 45:
            score += 1

        if diversification_metric >= 75:
            score += 2
        elif diversification_metric >= 55:
            score += 1

        if score >= 8:
            return "portfolio_optimizer_diversification_excellent"
        if score >= 6:
            return "portfolio_optimizer_diversification_good"
        if score >= 4:
            return "portfolio_optimizer_diversification_moderate"
        return "portfolio_optimizer_diversification_weak"

    def _health_explanation_key(self, *, score: float, emergency_months: float, largest_concentration_pct: float, asset_classes_owned: int, gold_pct: float) -> str:
        if score >= 85 and emergency_months >= 6 and largest_concentration_pct <= 50 and asset_classes_owned >= 2:
            return "portfolio_optimizer_health_explain_strong"
        if emergency_months < 6:
            return "portfolio_optimizer_health_explain_liquidity_gap"
        if gold_pct < self.RECOMMENDED_BANDS["gold"].min_pct:
            return "portfolio_optimizer_health_explain_gold_low"
        if largest_concentration_pct > 50:
            return "portfolio_optimizer_health_explain_concentration"
        return "portfolio_optimizer_health_explain_balanced"
