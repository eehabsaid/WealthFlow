from __future__ import annotations

from typing import Any, Dict


class GoldGrowthMixin:
    """Derives gold monthly growth rates and projects gold value forward."""

    def _gold_monthly_growth_rate(self, portfolio: Dict[str, Any]) -> float:
        trend_30_monthly = (portfolio["gold_trend_30"] / 100.0)
        trend_90_monthly = (portfolio["gold_trend_90"] / 100.0) / 3.0
        ma_bias_monthly = (portfolio["gold_ma_gap_pct"] / 100.0) / 2.0
        base_rate = (trend_30_monthly * 0.55) + (trend_90_monthly * 0.30) + (ma_bias_monthly * 0.15)
        return base_rate

    def _scenario_gold_rate(self, base_rate: float, scenario: str, portfolio: Dict[str, Any]) -> float:
        spread = max(abs(base_rate) * 0.35, (abs(portfolio["gold_signal"]) / 100.0) * 0.10)
        if scenario == "conservative":
            return base_rate - spread
        if scenario == "optimistic":
            return base_rate + spread
        return base_rate

    def _project_gold(self, current_value: float, months_ahead: int, monthly_rate: float) -> float:
        if current_value <= 0:
            return 0.0
        return max(0.0, current_value * ((1.0 + monthly_rate) ** months_ahead))
