from __future__ import annotations

from typing import Any, Dict

from core.services.financial_advisor.what_if_simulator_service.context import WhatIfContext
from core.services.financial_advisor.what_if_simulator_service.helpers import _clamp, _to_float


def clamp_params(ctx: WhatIfContext) -> None:
    """Clamp incoming parameters to valid ranges."""
    service = ctx.service
    ctx.salary_change_pct = _clamp(
        _to_float(ctx.salary_change_pct),
        service.SALARY_CHANGE_MIN,
        service.SALARY_CHANGE_MAX,
    )
    ctx.expenses_change_pct = _clamp(
        _to_float(ctx.expenses_change_pct),
        service.EXPENSES_CHANGE_MIN,
        service.EXPENSES_CHANGE_MAX,
    )
    if ctx.certificate_reinvestment_choice not in service.REINVESTMENT_OPTIONS:
        ctx.certificate_reinvestment_choice = "reinvest"


def fetch_current_values(ctx: WhatIfContext) -> None:
    """Fetch real current values and resolve the gold allocation target."""
    service = ctx.service
    ctx.current = service._current_values()
    ctx.gold_slider_max = ctx.current["gold_allocation_max_slider"]

    if ctx.gold_allocation_target_pct is None:
        ctx.gold_allocation_target_pct = ctx.current["gold_allocation_pct"]
    ctx.gold_allocation_target_pct = _clamp(
        _to_float(ctx.gold_allocation_target_pct), 0.0, ctx.gold_slider_max
    )

    ctx.monthly_salary = ctx.current["monthly_salary"]
    ctx.avg_monthly_expenses = ctx.current["monthly_expenses"]
    ctx.cash_balance = ctx.current["cash_balance"]
    ctx.total_net_worth = ctx.current["total_net_worth"]
    ctx.current_gold_pct = ctx.current["gold_allocation_pct"]
    ctx.current_gold_value = ctx.current["gold_value"]


def compute_baseline(ctx: WhatIfContext) -> None:
    """Baseline: all engines called with no overrides."""
    service = ctx.service
    ctx.baseline_series = service._compute_net_worth_series(None)
    ctx.baseline_points = ctx.baseline_series.get("points", [])
    ctx.baseline_nw_12m = ctx.baseline_points[-1]["net_worth"] if ctx.baseline_points else ctx.total_net_worth

    ctx.baseline_risk_score = service._compute_risk_score(None, None)

    ctx.baseline_cash_coverage = (
        round(ctx.cash_balance / ctx.avg_monthly_expenses, 1)
        if ctx.avg_monthly_expenses > 0 else None
    )


def build_forecast_overrides(ctx: WhatIfContext) -> None:
    """Build adjusted scenario overrides."""
    ctx.salary_scale = 1.0 + ctx.salary_change_pct / 100.0
    ctx.expense_scale = 1.0 + ctx.expenses_change_pct / 100.0

    # Gold value override: scale current gold to reach target % of net worth
    ctx.target_gold_value = None
    if ctx.total_net_worth > 0:
        ctx.target_gold_value = (ctx.gold_allocation_target_pct / 100.0) * ctx.total_net_worth

    forecast_overrides: Dict[str, Any] = {}
    if ctx.salary_scale != 1.0:
        forecast_overrides["monthly_salary_scale"] = ctx.salary_scale
    if ctx.expense_scale != 1.0:
        forecast_overrides["monthly_expense_scale"] = ctx.expense_scale
    if ctx.target_gold_value is not None and abs(ctx.target_gold_value - ctx.current_gold_value) > 0.01:
        forecast_overrides["gold_value"] = ctx.target_gold_value
    if ctx.certificate_reinvestment_choice == "cashout":
        forecast_overrides["certificate_reinvest"] = "cashout"
    ctx.forecast_overrides = forecast_overrides


def compute_adjusted(ctx: WhatIfContext) -> None:
    """Adjusted net worth series, risk score, and cash coverage."""
    service = ctx.service

    # ── Adjusted net worth series via existing engine ─────────────────
    ctx.adjusted_series = service._compute_net_worth_series(
        ctx.forecast_overrides if ctx.forecast_overrides else None
    )
    ctx.adjusted_points = ctx.adjusted_series.get("points", [])
    ctx.adjusted_nw_12m = ctx.adjusted_points[-1]["net_worth"] if ctx.adjusted_points else ctx.baseline_nw_12m

    # ── Adjusted risk score via RiskAnalysisService with overridden inputs
    adj_salary_for_risk = max(0.0, ctx.monthly_salary * ctx.salary_scale) if ctx.salary_change_pct != 0 else None
    adj_expenses_for_risk = max(0.0, ctx.avg_monthly_expenses * ctx.expense_scale) if ctx.expenses_change_pct != 0 else None
    ctx.adjusted_risk_score = service._compute_risk_score(adj_salary_for_risk, adj_expenses_for_risk)

    # ── Adjusted cash coverage via NetWorthService formula ────────────
    ctx.adjusted_cash_coverage = service._compute_cash_coverage(
        ctx.cash_balance, ctx.avg_monthly_expenses, ctx.salary_change_pct, ctx.expenses_change_pct
    )


def compute_deltas(ctx: WhatIfContext) -> None:
    """Deltas, favorability, and shared month labels."""
    ctx.nw_delta = round(ctx.adjusted_nw_12m - ctx.baseline_nw_12m, 2)
    ctx.risk_delta = round(ctx.adjusted_risk_score - ctx.baseline_risk_score, 1)
    ctx.coverage_delta = (
        round(
            (ctx.adjusted_cash_coverage or 0.0) - (ctx.baseline_cash_coverage or 0.0),
            1,
        )
        if ctx.adjusted_cash_coverage is not None and ctx.baseline_cash_coverage is not None
        else None
    )

    # Higher net worth = favorable; lower risk score = favorable; higher coverage = favorable
    ctx.nw_favorable = ctx.nw_delta > 0
    ctx.risk_favorable = ctx.risk_delta < 0
    ctx.coverage_favorable = (ctx.coverage_delta is not None and ctx.coverage_delta > 0)

    ctx.month_labels = ["Current"] + [
        pt["month_end"]
        for pt in ctx.baseline_points[1:]
    ]
