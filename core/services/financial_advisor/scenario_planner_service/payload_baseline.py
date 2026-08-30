"""Baseline computation phase of ScenarioPlannerService.payload().

Part of the payload() call chain (see payload.py for the orchestrator and
payload_scenarios.py for the per-scenario comparison phase).

NOTE (200-line file convention): extracted from the original monolithic
core/services/financial_advisor/scenario_planner_service.py (716 lines).
See __init__.py for the full package layout.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.services.financial_advisor.risk_analysis_service import RiskAnalysisService

from .config import _to_float


@dataclass
class BaselineContext:
    """Shared baseline inputs needed by the scenario comparison phase."""

    monthly_salary: float
    total_monthly_income: float
    avg_monthly_expenses: float
    cash_balance: float
    gold_pct: float
    real_debt_baseline: float
    baseline_pts: List[dict]
    baseline_nw_12m: float


def build_baseline(service) -> tuple[Dict[str, Any], BaselineContext]:
    """Computes the baseline trajectory dict + shared context for scenario comparison.

    `service` is the ScenarioPlannerService instance (passed explicitly rather
    than using a bound method, matching the NetWorthService phase-function
    pattern).
    """
    cert_forecast = service._net_worth_service.certificate_forecast_payload(today=service.today)
    comp = service._net_worth_service.portfolio_components()

    monthly_salary = _to_float(cert_forecast.get("monthly_salary"))
    monthly_cert_income = _to_float(cert_forecast.get("monthly_certificate_income"))
    monthly_rental_income = _to_float(cert_forecast.get("monthly_rental_income"))
    total_monthly_income = _to_float(cert_forecast.get("total_monthly_income"))
    if total_monthly_income <= 0:
        total_monthly_income = monthly_salary + monthly_cert_income + monthly_rental_income

    avg_monthly_expenses = _to_float(cert_forecast.get("avg_monthly_expenses"))
    cash_balance = _to_float(cert_forecast.get("cash_balance"))
    total_net_worth = _to_float(comp.get("net_worth_egp"))
    gold_value = _to_float(comp.get("gold_value_egp"))
    gold_pct = (gold_value / total_net_worth * 100.0) if total_net_worth > 0 else 0.0
    real_debt_baseline = service._get_current_real_debt()

    baseline_series_data = service._forecast_service.forecast_with_overrides("expected", {})
    baseline_pts = baseline_series_data.get("points", [])
    baseline_nw_12m = baseline_pts[-1]["net_worth"] if baseline_pts else 0.0

    baseline_risk_score = _to_float(
        RiskAnalysisService(today=service.today, net_worth_service=service._net_worth_service)
        .payload()
        .get("risk_score", {})
        .get("score")
    )
    baseline_goal_payload = service._goal_service.payload()
    baseline_goals_list = baseline_goal_payload.get("goals", [])
    if baseline_goals_list:
        unfavorable_statuses = {"at_risk", "critical"}
        favorable_count = sum(1 for g in baseline_goals_list if g.get("status") not in unfavorable_statuses)
        baseline_goal_pct = round((favorable_count / len(baseline_goals_list)) * 100.0, 1)
    else:
        baseline_goal_pct = 100.0

    baseline_coverage = round(cash_balance / avg_monthly_expenses, 1) if avg_monthly_expenses > 0 else None

    baseline_retire = service._compute_retirement_readiness(
        baseline_nw_12m, avg_monthly_expenses, service.config["DEFAULT_RETIREMENT_AGE"]
    )

    baseline_dict = {
        "id": 0,
        "name": "Baseline",
        "description": "Current active financial trajectory",
        "is_baseline_pinned": True,
        "net_worth_12m": round(baseline_nw_12m, 2),
        "monthly_salary": round(monthly_salary, 2),
        "monthly_income": round(total_monthly_income, 2),
        "monthly_expenses": round(avg_monthly_expenses, 2),
        "monthly_cash_flow": round(total_monthly_income - avg_monthly_expenses, 2),
        "total_debt": round(real_debt_baseline, 2),
        "cash_coverage_months": baseline_coverage,
        "risk_score": round(baseline_risk_score, 1),
        "goal_achievement_pct": baseline_goal_pct,
        "gold_allocation_pct": round(gold_pct, 1),
        "retirement_readiness": baseline_retire,
        "series": [
            {"month_end": pt["month_end"], "net_worth": pt["net_worth"]}
            for pt in baseline_pts
        ],
        "events": [],
    }

    ctx = BaselineContext(
        monthly_salary=monthly_salary,
        total_monthly_income=total_monthly_income,
        avg_monthly_expenses=avg_monthly_expenses,
        cash_balance=cash_balance,
        gold_pct=gold_pct,
        real_debt_baseline=real_debt_baseline,
        baseline_pts=baseline_pts,
        baseline_nw_12m=baseline_nw_12m,
    )
    return baseline_dict, ctx
