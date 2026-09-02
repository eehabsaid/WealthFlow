from __future__ import annotations

from core.services.financial_advisor.overview_service.context import OverviewContext


def gather_subservice_payloads(ctx: OverviewContext) -> None:
    """Phase 1: Gather all sub-service payloads."""
    service = ctx.service
    ctx.portfolio_comp = service.net_worth_service.portfolio_components()
    ctx.cash_flow_payload = service.cash_flow_service.payload()
    ctx.wealth_growth_payload = service.wealth_growth_service.payload()
    ctx.portfolio_payload = service.portfolio_service.payload()
    ctx.goal_payload = service.goal_service.payload()

    ctx.current_nw = float(ctx.wealth_growth_payload.get("current_net_worth", 0.0))


def extract_portfolio_metrics(ctx: OverviewContext) -> None:
    """Phase 2: Extract metrics from Portfolio Optimizer."""
    ctx.portfolio_health = ctx.portfolio_payload.get("health", {})
    ctx.health_score = float(ctx.portfolio_health.get("score", 0.0))
    ctx.expense_baseline = ctx.portfolio_payload.get("expense_baseline", {})
    ctx.avg_monthly_expenses = float(ctx.expense_baseline.get("avg_monthly_expenses", 0.0))
    ctx.emergency_months = float(ctx.expense_baseline.get("emergency_fund_months", 0.0))
    ctx.diversification = ctx.portfolio_payload.get("diversification", {})
    ctx.diversification_rating = ctx.diversification.get("portfolio_diversification_rating", "")
    ctx.largest_asset_concentration = ctx.diversification.get("largest_asset_concentration", {})


def extract_cash_flow_metrics(ctx: OverviewContext) -> None:
    """Phase 3: Extract metrics from Cash Flow Forecast."""
    ctx.current_cash = float(ctx.cash_flow_payload.get("checkpoints", {}).get("current", 0.0))
    ctx.expected_change_30d = float(ctx.cash_flow_payload.get("day_checkpoints", {}).get("days_30", 0.0)) - ctx.current_cash
    ctx.largest_event = ctx.cash_flow_payload.get("summary", {}).get("largest_cash_event", {})
    ctx.nearest_maturity = ctx.cash_flow_payload.get("summary", {}).get("nearest_certificate_maturity", {})


def extract_wealth_growth_metrics(ctx: OverviewContext) -> None:
    """Phase 4: Extract metrics from Wealth Growth Projections."""
    ctx.expected_growth_pct = float(ctx.wealth_growth_payload.get("summary", {}).get("expected_growth_pct", 0.0))
    ctx.expected_net_worth_1y = float(ctx.wealth_growth_payload.get("checkpoints", {}).get("month_12", 0.0))


def extract_goal_metrics(ctx: OverviewContext) -> None:
    """Phase 5: Extract metrics from Goal Planning."""
    ctx.goal_summary = ctx.goal_payload.get("summary", {})
    ctx.goals_total = ctx.goal_summary.get("total_count", 0)
    ctx.goals_completed = ctx.goal_summary.get("completed_count", 0)
    ctx.goals_on_track = ctx.goal_summary.get("on_track_count", 0)
    ctx.goals_delayed = ctx.goal_summary.get("at_risk_count", 0)
    ctx.goal_progress_pct = ctx.goal_summary.get("overall_progress_pct", 0)


def extract_spending_trend(ctx: OverviewContext) -> None:
    """Phase 6: Extract spending trend from Cash Flow Timeline first month."""
    ctx.this_month_spending = 0.0
    ctx.timeline = ctx.cash_flow_payload.get("timeline", [])
    if ctx.timeline:
        for event in ctx.timeline[0].get("events", []):
            if event.get("type") == "expenses":
                ctx.this_month_spending = abs(float(event.get("amount", 0.0)))
                break

    ctx.spending_increase = 0.0
    if ctx.avg_monthly_expenses > 0:
        ctx.spending_increase = ((ctx.this_month_spending - ctx.avg_monthly_expenses) / ctx.avg_monthly_expenses) * 100.0
