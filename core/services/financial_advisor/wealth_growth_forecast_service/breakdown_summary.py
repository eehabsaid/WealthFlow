from __future__ import annotations

from typing import Any, Dict, List

from .utils import _to_float


class BreakdownSummaryMixin:
    """Computes per-component breakdown and the narrative growth summary."""

    def _breakdown(self, portfolio: Dict[str, Any], expected_points: List[Dict[str, Any]]) -> Dict[str, dict]:
        final = expected_points[-1]
        current_liquid = portfolio["current_cash"] + portfolio["bank_balances"]
        current_components = {
            "liquid_cash": current_liquid,
            "fixed_assets": portfolio["fixed_assets"],
            "gold": portfolio["gold_value"],
            "certificates": portfolio["certificate_value"],
        }
        forecast_components = {
            "liquid_cash": final["liquid_cash"],
            "fixed_assets": final["fixed_assets"],
            "gold": final["gold"],
            "certificates": final["certificates"],
        }
        breakdown = {}
        for key in current_components:
            current = _to_float(current_components[key])
            forecast = _to_float(forecast_components[key])
            diff = forecast - current
            growth_pct = (diff / current * 100.0) if current > 0 else (100.0 if forecast > 0 else 0.0)
            breakdown[key] = {
                "current": round(current, 2),
                "forecast": round(forecast, 2),
                "difference": round(diff, 2),
                "growth_pct": round(growth_pct, 2),
            }
        return breakdown

    def _summary(self, portfolio: Dict[str, Any], breakdown: Dict[str, dict], expected_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        current = portfolio["current_net_worth"]
        final = expected_points[-1]["net_worth"]
        increase = final - current
        growth_pct = (increase / current * 100.0) if current > 0 else 0.0

        positive_components = [
            (key, data["difference"], data["growth_pct"])
            for key, data in breakdown.items()
            if _to_float(data["difference"]) > 0 and key not in ("liquid_cash", "certificates")
        ]
        largest_appreciating_asset = max(positive_components, key=lambda item: item[1], default=None)
        fastest_growing_category = max(positive_components, key=lambda item: item[2], default=None)

        cashflow_driver_totals: Dict[str, float] = {}
        for month in portfolio.get("cash_timeline", []):
            for event in month.get("events", []):
                event_type = str(event.get("type") or "")
                amount = _to_float(event.get("amount"))
                if amount <= 0:
                    continue
                cashflow_driver_totals[event_type] = cashflow_driver_totals.get(event_type, 0.0) + amount

        driver_candidates = {
            "salary": cashflow_driver_totals.get("salary", 0.0),
            "certificates": (
                cashflow_driver_totals.get("certificate_interest", 0.0)
                + cashflow_driver_totals.get("certificate_maturity", 0.0)
            ),
            "rental_income": cashflow_driver_totals.get("rental_income", 0.0),
            "asset_sale": cashflow_driver_totals.get("asset_sale", 0.0),
            "gold": max(0.0, _to_float(breakdown.get("gold", {}).get("difference"))),
            "fixed_assets": max(0.0, _to_float(breakdown.get("fixed_assets", {}).get("difference"))),
        }
        largest_driver_key, largest_driver_amount = max(
            driver_candidates.items(),
            key=lambda item: item[1],
            default=("none", 0.0),
        )

        insight_key = "wealth_growth_insight_balanced"
        if increase <= 0 or largest_driver_amount <= 0:
            insight_key = "wealth_growth_insight_flat"
        elif largest_driver_key == "salary":
            insight_key = "wealth_growth_insight_salary"
        elif largest_driver_key == "rental_income":
            insight_key = "wealth_growth_insight_rental_income"
        elif largest_driver_key == "asset_sale":
            insight_key = "wealth_growth_insight_asset_sale"
        elif largest_driver_key == "gold":
            insight_key = "wealth_growth_insight_gold"
        elif largest_driver_key == "certificates":
            insight_key = "wealth_growth_insight_certificates"
        elif largest_driver_key == "fixed_assets":
            insight_key = "wealth_growth_insight_fixed_assets"

        return {
            "expected_net_worth_increase": round(increase, 2),
            "expected_growth_pct": round(growth_pct, 2),
            "largest_appreciating_asset": {
                "key": largest_appreciating_asset[0],
                "difference": round(_to_float(largest_appreciating_asset[1]), 2),
            } if largest_appreciating_asset else None,
            "fastest_growing_asset_category": {
                "key": fastest_growing_category[0],
                "growth_pct": round(_to_float(fastest_growing_category[2]), 2),
            } if fastest_growing_category else None,
            "largest_growth_driver": {
                "key": largest_driver_key,
                "amount": round(_to_float(largest_driver_amount), 2),
            },
            "estimated_monthly_wealth_increase": round(increase / 12.0 if increase else 0.0, 2),
            "insight_key": insight_key,
        }
