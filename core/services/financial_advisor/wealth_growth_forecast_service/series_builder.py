from __future__ import annotations

from typing import Any, Dict, List

from .utils import _to_float


class SeriesBuilderMixin:
    """Builds the month-by-month forecast series for a given scenario."""

    def _month_end_cash(self, cash_timeline: List[dict], month_index: int) -> float:
        if month_index <= 0:
            return _to_float(cash_timeline[0].get("ending_cash") if cash_timeline else 0)
        if not cash_timeline:
            return 0.0
        index = min(month_index, len(cash_timeline) - 1)
        return _to_float(cash_timeline[index].get("ending_cash"))

    def _component_forecast(self, portfolio: Dict[str, Any], month_index: int, scenario: str, gold_rate: float) -> Dict[str, Any]:
        month_end_dates = self._month_end_dates()
        month_end = month_end_dates[min(max(month_index - 1, 0), len(month_end_dates) - 1)] if month_index > 0 else self.today
        cash_timeline = portfolio["cash_timeline"]
        cash_value = portfolio["current_cash"] if month_index <= 0 else self._month_end_cash(cash_timeline, month_index)
        liquid_cash = cash_value + portfolio["bank_balances"]
        fixed_assets = portfolio["fixed_assets"]
        gold_value = self._project_gold(portfolio["gold_value"], month_index, gold_rate)
        certificate_value = self._active_certificate_principal_by_month(month_end)
        net_worth = liquid_cash + fixed_assets + gold_value + certificate_value
        return {
            "month_index": month_index,
            "month_end": month_end.isoformat(),
            "liquid_cash": round(liquid_cash, 2),
            "fixed_assets": round(fixed_assets, 2),
            "gold": round(gold_value, 2),
            "certificates": round(certificate_value, 2),
            "net_worth": round(net_worth, 2),
        }

    def _build_series(self, portfolio: Dict[str, Any], scenario: str) -> Dict[str, Any]:
        gold_base_rate = self._gold_monthly_growth_rate(portfolio)
        gold_rate = self._scenario_gold_rate(gold_base_rate, scenario, portfolio)
        points = [self._component_forecast(portfolio, month_index, scenario, gold_rate) for month_index in range(0, self.MONTHS_AHEAD + 1)]
        return {
            "scenario": scenario,
            "gold_monthly_rate": round(gold_rate * 100.0, 4),
            "points": points,
            "final_net_worth": points[-1]["net_worth"],
            "net_worth_increase": round(points[-1]["net_worth"] - portfolio["current_net_worth"], 2),
        }
