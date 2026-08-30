"""Per-scenario comparison phase of ScenarioPlannerService.payload().

Part of the payload() call chain (see payload.py for the orchestrator and
payload_baseline.py for the baseline computation phase).

NOTE (200-line file convention): extracted from the original monolithic
core/services/financial_advisor/scenario_planner_service.py (716 lines).
See __init__.py for the full package layout.
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.models import Scenario
from core.services.financial_advisor.goal_planning_service import GoalPlanningService
from core.services.financial_advisor.risk_analysis_service import RiskAnalysisService

from .config import _to_float
from .payload_baseline import BaselineContext


def build_scenarios(
    service,
    ctx: BaselineContext,
    baseline_dict: Dict[str, Any],
    scenario_ids: List[int] | None,
) -> List[Dict[str, Any]]:
    """Builds the N-way scenario comparison list against the baseline.

    `service` is the ScenarioPlannerService instance (passed explicitly rather
    than using a bound method, matching the NetWorthService phase-function
    pattern).
    """
    scenarios_out: List[Dict[str, Any]] = []
    if not scenario_ids:
        return scenarios_out

    scenarios_qs = (
        Scenario.objects.filter(id__in=scenario_ids)
        .prefetch_related("events")
        .order_by("id")
    )
    for sc in scenarios_qs:
        events = list(sc.events.all())
        overrides, added_debt, sc_target_age = service._events_to_overrides(
            events, monthly_salary=ctx.monthly_salary
        )

        # Series with scenario overrides
        sc_series_data = service._forecast_service.forecast_with_overrides("expected", overrides)
        sc_pts = sc_series_data.get("points", [])
        sc_nw_12m = sc_pts[-1]["net_worth"] if sc_pts else ctx.baseline_nw_12m

        # Salary / Expense deltas for risk and cash flow
        sal_scale = float(overrides.get("monthly_salary_scale", 1.0))
        sal_delta = float(overrides.get("monthly_salary_delta", 0.0))
        exp_scale = float(overrides.get("monthly_expense_scale", 1.0))
        exp_delta = float(overrides.get("monthly_expense_delta", 0.0))

        adj_salary = max(0.0, (ctx.monthly_salary * sal_scale) + sal_delta)
        adj_income = max(0.0, (ctx.total_monthly_income - ctx.monthly_salary) + adj_salary)
        adj_expenses = max(0.0, (ctx.avg_monthly_expenses * exp_scale) + exp_delta)

        # Net lump sum monthly impact over 12m projection
        total_lump_out = sum(_to_float(item.get("amount")) for item in overrides.get("lump_sum_outflows", []))
        total_lump_in = sum(_to_float(item.get("amount")) for item in overrides.get("lump_sum_inflows", []))
        lump_monthly_net = (total_lump_out - total_lump_in) / 12.0

        sc_risk_svc = RiskAnalysisService(
            today=service.today,
            net_worth_service=service._net_worth_service,
            salary_override=adj_salary if adj_salary != ctx.monthly_salary else None,
            monthly_expenses_override=adj_expenses if adj_expenses != ctx.avg_monthly_expenses else None,
        )
        sc_risk_score = _to_float(sc_risk_svc.payload().get("risk_score", {}).get("score"))

        sc_coverage = round(ctx.cash_balance / adj_expenses, 1) if adj_expenses > 0 else None
        sc_total_debt = ctx.real_debt_baseline + added_debt

        # Retirement readiness presentation metric
        target_age_to_use = sc_target_age if sc_target_age is not None else service.config["DEFAULT_RETIREMENT_AGE"]
        sc_retire = service._compute_retirement_readiness(
            sc_nw_12m, adj_expenses, target_age_to_use
        )

        # Per-scenario capacity-sensitive goal achievement (% of goals with sufficient monthly capacity)
        sc_monthly_capacity = max(0.0, (adj_income - adj_expenses) - lump_monthly_net)
        sc_goal_svc = GoalPlanningService(
            today=service.today,
            net_worth_service=service._net_worth_service,
            monthly_capacity_override=sc_monthly_capacity,
        )
        sc_goal_payload = sc_goal_svc.payload()
        sc_goals_list = sc_goal_payload.get("goals", [])
        if sc_goals_list:
            unfavorable_statuses = {"at_risk", "critical"}
            favorable_count = sum(1 for g in sc_goals_list if g.get("status") not in unfavorable_statuses)
            sc_goal_pct = round((favorable_count / len(sc_goals_list)) * 100.0, 1)
        else:
            sc_goal_pct = 100.0

        sc_dict = {
            "id": sc.id,
            "name": sc.name,
            "description": sc.description,
            "is_baseline_pinned": sc.is_baseline_pinned,
            "net_worth_12m": round(sc_nw_12m, 2),
            "monthly_salary": round(adj_salary, 2),
            "monthly_income": round(adj_income, 2),
            "monthly_expenses": round(adj_expenses, 2),
            "monthly_cash_flow": round(adj_income - adj_expenses, 2),
            "total_debt": round(sc_total_debt, 2),
            "cash_coverage_months": sc_coverage,
            "risk_score": round(sc_risk_score, 1),
            "goal_achievement_pct": round(sc_goal_pct, 1),
            "gold_allocation_pct": round(ctx.gold_pct, 1),
            "retirement_readiness": sc_retire,
            "series": [
                {"month_end": pt["month_end"], "net_worth": pt["net_worth"]}
                for pt in sc_pts
            ],
            "events": [ev.to_dict() for ev in events],
        }
        sc_dict["insights"] = service.generate_insights(baseline_dict, sc_dict)
        scenarios_out.append(sc_dict)

    return scenarios_out
