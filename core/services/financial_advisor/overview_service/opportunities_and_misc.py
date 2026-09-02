from __future__ import annotations

import datetime

from core.services.financial_advisor.overview_service.context import OverviewContext


def build_opportunities(ctx: OverviewContext) -> None:
    """Phase 9: Map opportunities and bind target_tab and priorities."""
    opportunities = []
    for opp in ctx.portfolio_payload.get("opportunities", []):
        target_tab = "portfolio-optimizer"
        if opp.get("key", "").startswith("cash_flow") or opp.get("key", "").startswith("portfolio_optimizer_opp_improve_liquidity"):
            target_tab = "cash-flow-forecast"

        opp_priority = str(opp.get("severity", "medium")).lower()
        if opp_priority not in ["high", "medium", "low"]:
            opp_priority = "medium"

        opportunities.append({
            "priority": opp_priority,
            "key": opp.get("key"),
            "impact_key": opp.get("impact_key"),
            "target_tab": target_tab
        })
    ctx.opportunities = opportunities


def build_sparklines(ctx: OverviewContext) -> None:
    """Phase 10: Extract sparkline points."""
    ctx.cash_sparkline = [{"month": p.get("month"), "balance": p.get("balance")} for p in ctx.timeline[:6]]
    wealth_timeline = ctx.wealth_growth_payload.get("series", {}).get("expected", {}).get("points", [])
    ctx.wealth_sparkline = [{"month": p.get("month_end")[:7], "balance": p.get("net_worth")} for p in wealth_timeline[:6]]


def determine_next_goal(ctx: OverviewContext) -> None:
    """Phase 11: Determine next goal due from all goals."""
    active_goals = [g for g in ctx.goal_payload.get("goals", []) if g.get("status") != "Completed" and g.get("target_date")]
    ctx.next_goal = None
    if active_goals:
        active_goals_sorted = sorted(active_goals, key=lambda g: g.get("target_date"))
        ctx.next_goal = {
            "name": active_goals_sorted[0]["name"],
            "target_date": active_goals_sorted[0]["target_date"]
        }


def build_as_of(ctx: OverviewContext) -> None:
    """Phase 12: Localized Date Components."""
    now = datetime.datetime.now()
    ctx.as_of_dict = {
        "day": now.day,
        "month_key": f"month_short_{now.month}",
        "year": now.year,
        "time": now.strftime("%H:%M")
    }
