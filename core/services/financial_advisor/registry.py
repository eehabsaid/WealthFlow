"""
Centralized Financial Advisor Service Registry.

Provides a unified interface for fetching advisor payloads by service key
without coupling consumer components (e.g., ContextBuilder) directly to concrete service classes.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.financial_advisor.goal_planning_service import GoalPlanningService
from core.services.financial_advisor.opportunity_detection_service import OpportunityDetectionService
from core.services.financial_advisor.overview_service import OverviewService
from core.services.financial_advisor.performance_service import PerformanceService
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.risk_analysis_service import RiskAnalysisService
from core.services.financial_advisor.scenario_planner_service import ScenarioPlannerService
from core.services.financial_advisor.spending_intelligence_service import SpendingIntelligenceService
from core.services.financial_advisor.wealth_growth_forecast_service import WealthGrowthForecastService
from core.services.financial_advisor.what_if_simulator_service import WhatIfSimulatorService


def _fetch_overview_payload(today: datetime.date | None = None) -> dict[str, Any]:
    return OverviewService(today=today).payload()


def _fetch_cash_flow_payload(today: datetime.date | None = None) -> dict[str, Any]:
    return CashFlowForecastService(today=today).payload()


def _fetch_wealth_growth_payload(today: datetime.date | None = None) -> dict[str, Any]:
    return WealthGrowthForecastService(today=today).payload()


def _fetch_portfolio_optimizer_payload(today: datetime.date | None = None) -> dict[str, Any]:
    return PortfolioOptimizerService(today=today).payload()


def _fetch_goal_planning_payload(today: datetime.date | None = None) -> dict[str, Any]:
    return GoalPlanningService(today=today).payload()


def _fetch_risk_analysis_payload(today: datetime.date | None = None) -> dict[str, Any]:
    return RiskAnalysisService(today=today).payload()


def _fetch_spending_intelligence_payload(today: datetime.date | None = None) -> dict[str, Any]:
    return SpendingIntelligenceService(today=today).payload()


def _fetch_opportunity_detection_payload(today: datetime.date | None = None) -> dict[str, Any]:
    return OpportunityDetectionService(today=today).payload()


def _fetch_performance_payload(today: datetime.date | None = None) -> dict[str, Any]:
    return PerformanceService(today=today).payload()


def _fetch_what_if_simulator_payload(today: datetime.date | None = None) -> dict[str, Any]:
    return WhatIfSimulatorService(today=today).payload()


def _fetch_scenario_planner_payload(today: datetime.date | None = None) -> dict[str, Any]:
    return ScenarioPlannerService(today=today).payload()


ADVISOR_SERVICE_PROVIDERS: dict[str, Callable[[datetime.date | None], dict[str, Any]]] = {
    "overview": _fetch_overview_payload,
    "cash_flow": _fetch_cash_flow_payload,
    "wealth_growth": _fetch_wealth_growth_payload,
    "portfolio_optimizer": _fetch_portfolio_optimizer_payload,
    "goal_planning": _fetch_goal_planning_payload,
    "risk_analysis": _fetch_risk_analysis_payload,
    "spending_intelligence": _fetch_spending_intelligence_payload,
    "opportunity_detection": _fetch_opportunity_detection_payload,
    "performance": _fetch_performance_payload,
    "what_if_simulator": _fetch_what_if_simulator_payload,
    "scenario_planner": _fetch_scenario_planner_payload,
}


def get_financial_advisor_payload(service_key: str, today: datetime.date | None = None) -> dict[str, Any]:
    """
    Retrieve payload dict for a given service key.
    Returns empty dict if service key is unknown.
    """
    key = str(service_key or "").strip().lower()
    provider = ADVISOR_SERVICE_PROVIDERS.get(key)
    if not provider:
        return {}
    try:
        return provider(today)
    except Exception as exc:
        logger.warning(
            "Failed to retrieve payload for financial advisor service '%s': %s",
            key,
            exc,
            exc_info=True,
        )
        return {}


def get_available_advisor_services() -> list[str]:
    """Return list of supported service keys."""
    return list(ADVISOR_SERVICE_PROVIDERS.keys())
