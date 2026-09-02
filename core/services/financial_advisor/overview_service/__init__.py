"""
core/services/financial_advisor/overview_service package.

Sibling modules:
- context.py                  — OverviewContext dataclass threading state across phases
- metrics_extraction.py       — phases 1-6: gather sub-service payloads and extract
                                  portfolio / cash-flow / wealth-growth / goal / spending metrics
- alerts.py                   — phase 7: dynamic alerts list
- ai_summary.py                — phase 8: structured AI executive summary
- opportunities_and_misc.py   — phases 9-12: opportunities, sparklines, next goal due,
                                  localized date components

This file re-exports OverviewService, the public entry point.
"""

from __future__ import annotations

import datetime

from core.services.balance.net_worth_service import NetWorthService
from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.financial_advisor.wealth_growth_forecast_service import WealthGrowthForecastService
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.goal_planning_service import GoalPlanningService

from core.services.financial_advisor.overview_service.context import OverviewContext
from core.services.financial_advisor.overview_service.metrics_extraction import (
    gather_subservice_payloads,
    extract_portfolio_metrics,
    extract_cash_flow_metrics,
    extract_wealth_growth_metrics,
    extract_goal_metrics,
    extract_spending_trend,
)
from core.services.financial_advisor.overview_service.alerts import build_alerts
from core.services.financial_advisor.overview_service.ai_summary import build_executive_summary
from core.services.financial_advisor.overview_service.opportunities_and_misc import (
    build_opportunities,
    build_sparklines,
    determine_next_goal,
    build_as_of,
)


class OverviewService:
    def __init__(self, today: datetime.date | None = None, net_worth_service: NetWorthService | None = None):
        self.today = today or datetime.date.today()
        self.net_worth_service = net_worth_service or NetWorthService()
        self.cash_flow_service = CashFlowForecastService(today=self.today, net_worth_service=self.net_worth_service)
        self.wealth_growth_service = WealthGrowthForecastService(today=self.today, net_worth_service=self.net_worth_service)
        self.portfolio_service = PortfolioOptimizerService(today=self.today, net_worth_service=self.net_worth_service)
        self.goal_service = GoalPlanningService(today=self.today, net_worth_service=self.net_worth_service)

    def payload(self) -> dict:
        ctx = OverviewContext(service=self)

        gather_subservice_payloads(ctx)
        extract_portfolio_metrics(ctx)
        extract_cash_flow_metrics(ctx)
        extract_wealth_growth_metrics(ctx)
        extract_goal_metrics(ctx)
        extract_spending_trend(ctx)
        build_alerts(ctx)
        build_executive_summary(ctx)
        build_opportunities(ctx)
        build_sparklines(ctx)
        determine_next_goal(ctx)
        build_as_of(ctx)

        return {
            "as_of": ctx.as_of_dict,
            "health_score": round(ctx.health_score),
            "health_status_key": ctx.portfolio_health.get("label_key", "portfolio_optimizer_health_good"),
            "health_desc_key": ctx.portfolio_health.get("explanation_key", "portfolio_optimizer_health_explain_strong"),
            "executive_summary": ctx.executive_summary,
            "alerts": ctx.alerts_sorted,
            "kpis": {
                "total_net_worth": ctx.current_nw,
                "net_worth_growth_yoy": ctx.expected_growth_pct,
                "liquid_assets": ctx.portfolio_comp.get("liquid_assets_total_egp", 0.0),
                "emergency_months": ctx.emergency_months,
                "fixed_assets": ctx.portfolio_comp.get("fixed_assets_total_egp", 0.0),
                "fixed_assets_pct": round((ctx.portfolio_comp.get("fixed_assets_total_egp", 0.0) / ctx.current_nw * 100.0) if ctx.current_nw > 0 else 0.0, 1),
                "portfolio_health": ctx.health_score,
                "portfolio_health_status_key": ctx.portfolio_health.get("label_key", "portfolio_optimizer_health_good")
            },
            "cash_flow": {
                "current_cash": ctx.current_cash,
                "expected_change_30d": ctx.expected_change_30d,
                "largest_event": ctx.largest_event,
                "sparkline": ctx.cash_sparkline,
                "target_tab": "cash-flow-forecast"
            },
            "wealth_growth": {
                "current_net_worth": ctx.current_nw,
                "expected_net_worth_1y": ctx.expected_net_worth_1y,
                "expected_growth_pct": ctx.expected_growth_pct,
                "cagr_3y": ctx.expected_growth_pct * 0.8,
                "sparkline": ctx.wealth_sparkline,
                "target_tab": "wealth-growth-forecast"
            },
            "opportunities": ctx.opportunities,
            "portfolio": {
                "health_score": ctx.health_score,
                "largest_asset_class_key": ctx.largest_asset_concentration.get("label_key", "portfolio_optimizer_asset_cash"),
                "largest_asset_class_pct": ctx.largest_asset_concentration.get("percentage", 0.0),
                "diversification_score": ctx.portfolio_payload.get("health", {}).get("metrics", {}).get("diversification", 100.0),
                "largest_concentration_key": ctx.largest_asset_concentration.get("label_key", "portfolio_optimizer_asset_cash"),
                "allocation_chart": ctx.portfolio_payload.get("allocation_chart", {}),
                "allocation_cards": ctx.portfolio_payload.get("allocation", {}).get("cards", []),
                "total_portfolio": ctx.portfolio_payload.get("allocation", {}).get("total", 0.0),
                "target_tab": "portfolio-optimizer"
            },
            "goals": {
                "total": ctx.goals_total,
                "completed": ctx.goals_completed,
                "on_track": ctx.goals_on_track,
                "delayed": ctx.goals_delayed,
                "progress_pct": ctx.goal_progress_pct,
                "next_goal_due": ctx.next_goal,
                "target_tab": "goal-planning"
            }
        }


__all__ = ["OverviewService"]
