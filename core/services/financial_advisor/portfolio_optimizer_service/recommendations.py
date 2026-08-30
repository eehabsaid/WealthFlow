"""Rule-based recommendations derived from allocation percentages.

NOTE (200-line file convention): part of the split of
core/services/financial_advisor/portfolio_optimizer_service.py (659 lines).
"""
from __future__ import annotations

from typing import Dict, List

from .shared import _to_float


class RecommendationsMixin:
    def _recommendations(self, percentages: Dict[str, float], emergency_months: float) -> List[dict]:
        recommendations: List[dict] = []

        def add(key: str, severity: str, metric_value: float | None = None):
            if any(item["key"] == key for item in recommendations):
                return
            recommendations.append(
                {
                    "key": key,
                    "severity": severity,
                    "severity_key": f"portfolio_optimizer_severity_{severity}",
                    "metric_value": round(metric_value, 2) if metric_value is not None else None,
                }
            )

        cash_pct = _to_float(percentages.get("cash"))
        gold_pct = _to_float(percentages.get("gold"))
        real_estate_pct = _to_float(percentages.get("real_estate"))
        vehicle_pct = _to_float(percentages.get("vehicles"))
        cert_pct = _to_float(percentages.get("certificates"))

        largest_concentration = max((_to_float(value) for value in percentages.values()), default=0.0)
        recommended_gold_min = self.RECOMMENDED_BANDS["gold"].min_pct
        recommended_cash_max = self.RECOMMENDED_BANDS["cash"].max_pct

        if emergency_months < 6.0:
            add("portfolio_optimizer_rec_emergency_fund_low", "high", emergency_months)
        if cash_pct > recommended_cash_max:
            add("portfolio_optimizer_rec_cash_too_high", "medium", cash_pct)
        if 0.0 < gold_pct < recommended_gold_min:
            add("portfolio_optimizer_rec_gold_too_low", "medium", gold_pct)
        if gold_pct > 30.0:
            add("portfolio_optimizer_rec_gold_too_high", "medium", gold_pct)
        if real_estate_pct > 70.0:
            add("portfolio_optimizer_rec_real_estate_too_high", "medium", real_estate_pct)
        elif real_estate_pct >= 30.0:
            add("portfolio_optimizer_rec_real_estate_strength", "info", real_estate_pct)
        if vehicle_pct > 20.0:
            add("portfolio_optimizer_rec_vehicles_too_high", "low", vehicle_pct)
        if cert_pct > 50.0:
            add("portfolio_optimizer_rec_certificates_too_high", "medium", cert_pct)

        if largest_concentration <= 50.0:
            add("portfolio_optimizer_rec_no_concentration_risk", "info", largest_concentration)

        if not recommendations:
            add("portfolio_optimizer_rec_well_positioned", "info")

        priority_rank = {"high": 0, "medium": 1, "low": 2, "info": 3}
        recommendations.sort(key=lambda item: priority_rank.get(str(item.get("severity")), 99))

        return recommendations
