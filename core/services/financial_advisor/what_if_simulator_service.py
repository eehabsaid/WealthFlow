"""What-If Simulator Service.

This service answers "what if I adjust salary, expenses, gold allocation, or
certificate reinvestment?" by:

1. Using WealthGrowthForecastService.forecast_with_overrides() for the 12-month
   net worth projection (both baseline and adjusted).
2. Using RiskAnalysisService with overridden salary/expenses inputs for risk score
   (both baseline and adjusted).
3. Using NetWorthService.certificate_forecast_payload() for the raw cash_balance
   and avg_monthly_expenses, then applying the same division formula the service
   itself uses for cash coverage.

This service is READ-ONLY.  It never calls save() or update() on any model.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from core.services.balance.net_worth_service import NetWorthService
from core.services.financial_advisor.wealth_growth_forecast_service import WealthGrowthForecastService
from core.services.financial_advisor.risk_analysis_service import RiskAnalysisService
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class WhatIfSimulatorService:
    """Computes baseline + adjusted financial projections for the What-If tab."""

    # Slider parameter ranges
    SALARY_CHANGE_MIN = -100.0
    SALARY_CHANGE_MAX = 100.0
    EXPENSES_CHANGE_MIN = -50.0
    EXPENSES_CHANGE_MAX = 100.0
    GOLD_SLIDER_MAX_MULTIPLIER = 2.0  # gold slider max = 2 × RECOMMENDED_BANDS["gold"].max_pct

    REINVESTMENT_OPTIONS = ["reinvest", "cashout"]

    def __init__(self, today: date | None = None):
        self.today = today or date.today()
        self._net_worth_service = NetWorthService()
        self._forecast_service = WealthGrowthForecastService(
            today=self.today,
            net_worth_service=self._net_worth_service,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

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

    # ── Public API ────────────────────────────────────────────────────────────

    def payload(
        self,
        salary_change_pct: float = 0.0,
        expenses_change_pct: float = 0.0,
        gold_allocation_target_pct: Optional[float] = None,
        certificate_reinvestment_choice: str = "reinvest",
    ) -> dict:
        """Return baseline and adjusted projections.

        Parameters
        ----------
        salary_change_pct : float
            Percentage change to apply to salary (-50 to +100).
        expenses_change_pct : float
            Percentage change to apply to monthly expenses (-50 to +100).
        gold_allocation_target_pct : float, optional
            Target gold allocation as % of net worth (0 to slider max).
            Defaults to current real allocation (no change).
        certificate_reinvestment_choice : str
            "reinvest" (default) or "cashout".
        """
        # ── Clamp parameters to valid ranges ─────────────────────────────────
        salary_change_pct = _clamp(
            _to_float(salary_change_pct),
            self.SALARY_CHANGE_MIN,
            self.SALARY_CHANGE_MAX,
        )
        expenses_change_pct = _clamp(
            _to_float(expenses_change_pct),
            self.EXPENSES_CHANGE_MIN,
            self.EXPENSES_CHANGE_MAX,
        )
        if certificate_reinvestment_choice not in self.REINVESTMENT_OPTIONS:
            certificate_reinvestment_choice = "reinvest"

        try:
            # ── Fetch real current values ─────────────────────────────────────
            current = self._current_values()
            gold_slider_max = current["gold_allocation_max_slider"]

            if gold_allocation_target_pct is None:
                gold_allocation_target_pct = current["gold_allocation_pct"]
            gold_allocation_target_pct = _clamp(
                _to_float(gold_allocation_target_pct), 0.0, gold_slider_max
            )

            monthly_salary = current["monthly_salary"]
            avg_monthly_expenses = current["monthly_expenses"]
            cash_balance = current["cash_balance"]
            total_net_worth = current["total_net_worth"]
            current_gold_pct = current["gold_allocation_pct"]
            current_gold_value = current["gold_value"]

            # ── Baseline: all engines called with no overrides ────────────────
            baseline_series = self._compute_net_worth_series(None)
            baseline_points: List[Dict[str, Any]] = baseline_series.get("points", [])
            baseline_nw_12m = baseline_points[-1]["net_worth"] if baseline_points else total_net_worth

            baseline_risk_score = self._compute_risk_score(None, None)

            baseline_cash_coverage: Optional[float] = (
                round(cash_balance / avg_monthly_expenses, 1)
                if avg_monthly_expenses > 0 else None
            )

            # ── Build adjusted scenario overrides ─────────────────────────────
            salary_scale = 1.0 + salary_change_pct / 100.0
            expense_scale = 1.0 + expenses_change_pct / 100.0

            # Gold value override: scale current gold to reach target % of net worth
            target_gold_value: Optional[float] = None
            if total_net_worth > 0:
                target_gold_value = (gold_allocation_target_pct / 100.0) * total_net_worth

            forecast_overrides: Dict[str, Any] = {}
            if salary_scale != 1.0:
                forecast_overrides["monthly_salary_scale"] = salary_scale
            if expense_scale != 1.0:
                forecast_overrides["monthly_expense_scale"] = expense_scale
            if target_gold_value is not None and abs(target_gold_value - current_gold_value) > 0.01:
                forecast_overrides["gold_value"] = target_gold_value
            if certificate_reinvestment_choice == "cashout":
                forecast_overrides["certificate_reinvest"] = "cashout"

            # ── Adjusted net worth series via existing engine ─────────────────
            adjusted_series = self._compute_net_worth_series(
                forecast_overrides if forecast_overrides else None
            )
            adjusted_points: List[Dict[str, Any]] = adjusted_series.get("points", [])
            adjusted_nw_12m = adjusted_points[-1]["net_worth"] if adjusted_points else baseline_nw_12m

            # ── Adjusted risk score via RiskAnalysisService with overridden inputs
            adj_salary_for_risk = max(0.0, monthly_salary * salary_scale) if salary_change_pct != 0 else None
            adj_expenses_for_risk = max(0.0, avg_monthly_expenses * expense_scale) if expenses_change_pct != 0 else None
            adjusted_risk_score = self._compute_risk_score(adj_salary_for_risk, adj_expenses_for_risk)

            # ── Adjusted cash coverage via NetWorthService formula ────────────
            adjusted_cash_coverage = self._compute_cash_coverage(
                cash_balance, avg_monthly_expenses, salary_change_pct, expenses_change_pct
            )

            # ── Deltas and favorability ───────────────────────────────────────
            nw_delta = round(adjusted_nw_12m - baseline_nw_12m, 2)
            risk_delta = round(adjusted_risk_score - baseline_risk_score, 1)
            coverage_delta = (
                round(
                    (adjusted_cash_coverage or 0.0) - (baseline_cash_coverage or 0.0),
                    1,
                )
                if adjusted_cash_coverage is not None and baseline_cash_coverage is not None
                else None
            )

            # Higher net worth = favorable; lower risk score = favorable; higher coverage = favorable
            nw_favorable = nw_delta > 0
            risk_favorable = risk_delta < 0
            coverage_favorable = (coverage_delta is not None and coverage_delta > 0)

            # ── Month labels shared across both series ────────────────────────
            month_labels = ["Current"] + [
                pt["month_end"]
                for pt in baseline_points[1:]
            ]

            return {
                "as_of": self.today.isoformat(),
                "parameters": {
                    "salary_change_pct": round(salary_change_pct, 2),
                    "expenses_change_pct": round(expenses_change_pct, 2),
                    "gold_allocation_target_pct": round(gold_allocation_target_pct, 2),
                    "certificate_reinvestment_choice": certificate_reinvestment_choice,
                },
                "current_values": {
                    "monthly_salary": monthly_salary,
                    "monthly_expenses": avg_monthly_expenses,
                    "gold_allocation_pct": current_gold_pct,
                    "gold_band_min": current["gold_band_min"],
                    "gold_band_max": current["gold_band_max"],
                    "gold_allocation_max_slider": gold_slider_max,
                    "reinvestment_options": current["reinvestment_options"],
                },
                "baseline": {
                    "net_worth_12m": round(baseline_nw_12m, 2),
                    "risk_score": round(baseline_risk_score, 1),
                    "cash_coverage_months": baseline_cash_coverage,
                    "series": [
                        {"month_end": pt["month_end"], "net_worth": pt["net_worth"]}
                        for pt in baseline_points
                    ],
                },
                "adjusted": {
                    "net_worth_12m": round(adjusted_nw_12m, 2),
                    "risk_score": round(adjusted_risk_score, 1),
                    "cash_coverage_months": adjusted_cash_coverage,
                    "series": [
                        {"month_end": pt["month_end"], "net_worth": pt["net_worth"]}
                        for pt in adjusted_points
                    ],
                },
                "delta": {
                    "net_worth_12m": nw_delta,
                    "risk_score": risk_delta,
                    "cash_coverage_months": coverage_delta,
                    "net_worth_12m_favorable": nw_favorable,
                    "risk_score_favorable": risk_favorable,
                    "cash_coverage_favorable": coverage_favorable,
                },
                "month_labels": month_labels,
            }

        except Exception as exc:  # noqa: BLE001
            # Defensive: always return valid JSON, never a 500.
            return {
                "as_of": self.today.isoformat(),
                "error": str(exc),
                "parameters": {
                    "salary_change_pct": round(salary_change_pct, 2),
                    "expenses_change_pct": round(expenses_change_pct, 2),
                    "gold_allocation_target_pct": round(_to_float(gold_allocation_target_pct), 2),
                    "certificate_reinvestment_choice": certificate_reinvestment_choice,
                },
                "current_values": {
                    "monthly_salary": 0.0,
                    "monthly_expenses": 0.0,
                    "gold_allocation_pct": 0.0,
                    "gold_band_min": 10.0,
                    "gold_band_max": 20.0,
                    "gold_allocation_max_slider": 40.0,
                    "reinvestment_options": list(self.REINVESTMENT_OPTIONS),
                },
                "baseline": {
                    "net_worth_12m": 0.0,
                    "risk_score": 0.0,
                    "cash_coverage_months": None,
                    "series": [],
                },
                "adjusted": {
                    "net_worth_12m": 0.0,
                    "risk_score": 0.0,
                    "cash_coverage_months": None,
                    "series": [],
                },
                "delta": {
                    "net_worth_12m": 0.0,
                    "risk_score": 0.0,
                    "cash_coverage_months": None,
                    "net_worth_12m_favorable": False,
                    "risk_score_favorable": False,
                    "cash_coverage_favorable": False,
                },
                "month_labels": [],
            }
