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

Sibling modules:
- helpers.py            — _to_float, _clamp module-level helpers
- computation_mixin.py  — ComputationMixin: _current_values, _compute_net_worth_series,
                            _compute_risk_score, _compute_cash_coverage
- context.py            — WhatIfContext dataclass threading state across payload() phases
- payload_phases.py     — phase functions used by payload(): clamp_params, fetch_current_values,
                            compute_baseline, build_forecast_overrides, compute_adjusted, compute_deltas
- payload_builders.py   — build_success_payload, build_error_payload

This file re-exports WhatIfSimulatorService, the public entry point.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.services.balance.net_worth_service import NetWorthService
from core.services.financial_advisor.wealth_growth_forecast_service import WealthGrowthForecastService

from core.services.financial_advisor.what_if_simulator_service.computation_mixin import ComputationMixin
from core.services.financial_advisor.what_if_simulator_service.context import WhatIfContext
from core.services.financial_advisor.what_if_simulator_service.payload_phases import (
    clamp_params,
    fetch_current_values,
    compute_baseline,
    build_forecast_overrides,
    compute_adjusted,
    compute_deltas,
)
from core.services.financial_advisor.what_if_simulator_service.payload_builders import (
    build_success_payload,
    build_error_payload,
)


class WhatIfSimulatorService(ComputationMixin):
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
        ctx = WhatIfContext(
            service=self,
            salary_change_pct=salary_change_pct,
            expenses_change_pct=expenses_change_pct,
            gold_allocation_target_pct=gold_allocation_target_pct,
            certificate_reinvestment_choice=certificate_reinvestment_choice,
        )

        # ── Clamp parameters to valid ranges ─────────────────────────────────
        clamp_params(ctx)

        try:
            fetch_current_values(ctx)
            compute_baseline(ctx)
            build_forecast_overrides(ctx)
            compute_adjusted(ctx)
            compute_deltas(ctx)
            return build_success_payload(ctx)
        except Exception as exc:  # noqa: BLE001
            return build_error_payload(ctx, exc)


__all__ = ["WhatIfSimulatorService"]
