"""Rule-based opportunities derived from recommendations, plus a small
top-assets helper (highest appreciating asset) used alongside them.

NOTE (200-line file convention): part of the split of
core/services/financial_advisor/portfolio_optimizer_service.py (659 lines).
"""
from __future__ import annotations

from typing import Dict, List

from .shared import _to_float


class OpportunitiesMixin:
    def _opportunities(self, percentages: Dict[str, float], recommendations: List[dict], comp: dict) -> List[dict]:
        opportunities: List[dict] = []

        def add(key: str, impact_key: str, severity: str):
            if any(item["key"] == key for item in opportunities):
                return
            opportunities.append(
                {
                    "key": key,
                    "impact_key": impact_key,
                    "severity": severity,
                    "severity_key": f"portfolio_optimizer_severity_{severity}",
                }
            )

        recommendation_keys = {item["key"] for item in recommendations}
        cash_pct = _to_float(percentages.get("cash"))
        gold_pct = _to_float(percentages.get("gold"))
        emergency_months = self._emergency_fund_months(
            _to_float(comp.get("allocation_values", {}).get("type_cash"))
            + _to_float(comp.get("allocation_values", {}).get("bank_certificates")),
            self._monthly_expense_average(),
        )

        maturity_egp_90 = self._upcoming_certificate_maturity_egp(comp, days=90)
        concentration_pct = max((_to_float(value) for value in percentages.values()), default=0.0)

        if "portfolio_optimizer_rec_cash_too_high" in recommendation_keys:
            add("portfolio_optimizer_opp_reduce_idle_cash", "portfolio_optimizer_opp_impact_idle_cash", "medium")
        if "portfolio_optimizer_rec_certificates_too_high" in recommendation_keys and concentration_pct > 35.0:
            add("portfolio_optimizer_opp_diversify_certificates", "portfolio_optimizer_opp_impact_reduce_concentration", "low")
        if "portfolio_optimizer_rec_gold_too_low" in recommendation_keys:
            add("portfolio_optimizer_opp_increase_gold", "portfolio_optimizer_opp_impact_gold_balance", "medium")
        if "portfolio_optimizer_rec_vehicles_too_high" in recommendation_keys:
            add("portfolio_optimizer_opp_reduce_vehicle_exposure", "portfolio_optimizer_opp_impact_rebalance_assets", "low")

        if maturity_egp_90 > 0:
            add("portfolio_optimizer_opp_reinvest_maturities", "portfolio_optimizer_opp_impact_reinvest_maturities", "low")

        if emergency_months < 6.0 and cash_pct < 20.0:
            add("portfolio_optimizer_opp_improve_liquidity", "portfolio_optimizer_opp_impact_cash_buffer", "low")

        if not opportunities and cash_pct > self.RECOMMENDED_BANDS["cash"].max_pct and gold_pct < self.RECOMMENDED_BANDS["gold"].min_pct:
            add("portfolio_optimizer_opp_shift_cash_to_gold", "portfolio_optimizer_opp_impact_balance_allocation", "medium")

        return opportunities[:5]

    def _highest_appreciating_asset(self, top_assets: List[dict]) -> dict:
        if not top_assets:
            return {"asset": "-", "gain_pct": 0.0, "gain": 0.0}

        best = max(top_assets, key=lambda item: _to_float(item.get("gain_pct")))
        return {
            "asset": best.get("asset") or "-",
            "gain_pct": round(_to_float(best.get("gain_pct")), 2),
            "gain": round(_to_float(best.get("gain")), 2),
        }
