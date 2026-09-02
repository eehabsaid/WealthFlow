from __future__ import annotations

from typing import Any, Dict, Optional

from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.risk_analysis_service import RiskAnalysisService
from core.services.financial_advisor.what_if_simulator_service.helpers import _to_float


class ComputationMixin:
    """Engine calls: current values, net-worth series, risk score, cash coverage."""

    def _current_values(self) -> Dict[str, Any]:
        """Fetch real current portfolio values.  Called once per payload() call."""
        cert_forecast = self._net_worth_service.certificate_forecast_payload(today=self.today)
        comp = self._net_worth_service.portfolio_components()

        monthly_salary = _to_float(cert_forecast.get("monthly_salary"))
        avg_monthly_expenses = _to_float(cert_forecast.get("avg_monthly_expenses"))
        cash_balance = _to_float(cert_forecast.get("cash_balance"))

        total_net_worth = _to_float(comp.get("net_worth_egp"))
        gold_value = _to_float(comp.get("gold_value_egp"))
        gold_pct = (gold_value / total_net_worth * 100.0) if total_net_worth > 0 else 0.0

        gold_band = PortfolioOptimizerService.RECOMMENDED_BANDS.get("gold")
        gold_band_min = gold_band.min_pct if gold_band else 10.0
        gold_band_max = gold_band.max_pct if gold_band else 20.0
        gold_slider_max = gold_band_max * self.GOLD_SLIDER_MAX_MULTIPLIER

        return {
            "monthly_salary": round(monthly_salary, 2),
            "monthly_expenses": round(avg_monthly_expenses, 2),
            "cash_balance": round(cash_balance, 2),
            "gold_value": round(gold_value, 2),
            "total_net_worth": round(total_net_worth, 2),
            "gold_allocation_pct": round(gold_pct, 2),
            "gold_band_min": gold_band_min,
            "gold_band_max": gold_band_max,
            "gold_allocation_max_slider": gold_slider_max,
            "reinvestment_options": list(self.REINVESTMENT_OPTIONS),
        }

    def _compute_net_worth_series(self, scenario_overrides: dict | None) -> Dict[str, Any]:
        """Return the expected-scenario 12-month series via forecast_with_overrides().
        When scenario_overrides is None or empty, output is identical to _build_series()."""
        series = self._forecast_service.forecast_with_overrides("expected", scenario_overrides)
        return series

    def _compute_risk_score(
        self,
        salary_override: Optional[float],
        monthly_expenses_override: Optional[float],
    ) -> float:
        """Call RiskAnalysisService itself with overridden inputs.  No scoring math is
        duplicated — the service's complete payload() pipeline runs with injected values."""
        svc = RiskAnalysisService(
            today=self.today,
            net_worth_service=self._net_worth_service,
            salary_override=salary_override,
            monthly_expenses_override=monthly_expenses_override,
        )
        payload = svc.payload()
        return _to_float(payload.get("risk_score", {}).get("score"))

    def _compute_cash_coverage(
        self,
        cash_balance: float,
        avg_monthly_expenses: float,
        salary_change_pct: float,
        expenses_change_pct: float,
    ) -> Optional[float]:
        """Compute cash coverage using the same formula as NetWorthService.

        Formula (from NetWorthService.certificate_forecast_payload, line 545):
            cash_coverage_months = cash_balance / avg_monthly_expenses

        We apply overrides to the inputs obtained from NetWorthService (not
        hardcoded), then re-apply the exact same division.

        Salary change over 12 months adds to the cash balance as accumulated
        additional inflow.  Expense change alters the monthly burn rate.
        """
        salary_delta_12m = cash_balance * (salary_change_pct / 100.0)  # proxy: salary ~ (cash balance / 12)
        # More precise: if we have monthly_salary we add 12 * monthly_salary_delta
        # but cash_balance already reflects current cash; we use it as a proportion.
        adjusted_cash = max(0.0, cash_balance + salary_delta_12m)
        adjusted_expenses = avg_monthly_expenses * (1.0 + expenses_change_pct / 100.0)
        adjusted_expenses = max(0.0, adjusted_expenses)
        if adjusted_expenses <= 0:
            return None
        return round(adjusted_cash / adjusted_expenses, 1)
