"""
AI Tool Handlers — Scenario, Report & Optimization group.

NOTE (200-line file convention): part of the core/services/ai/tools/
package (see tools/__init__.py for the full convention). If this file
grows past 200 lines, split it further into more files within this same
package.
"""

from __future__ import annotations

from typing import Any

from core.services.financial_advisor.registry import get_financial_advisor_payload
from core.services.financial_advisor.scenario_planner_service import (
    ScenarioPlannerService,
    create_scenario_record,
)
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.opportunity_detection_service import OpportunityDetectionService


def _handle_create_scenario(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Wraps atomic scenario creation via create_scenario_record."""
    name = str(params.get("name", "")).strip()
    description = str(params.get("description", "")).strip()
    is_baseline_pinned = bool(params.get("is_baseline_pinned", False))
    events = params.get("events", [])
    sc = create_scenario_record(
        name=name,
        description=description,
        is_baseline_pinned=is_baseline_pinned,
        events=events,
    )
    return sc.to_dict()


def _handle_compare_scenarios(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Wraps ScenarioPlannerService.payload with scenario_ids."""
    scenario_ids = params.get("scenario_ids", [])
    svc = ScenarioPlannerService(user=user)
    return svc.payload(scenario_ids=scenario_ids)


def _handle_summarize_report(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Wraps get_financial_advisor_payload for a service key."""
    service_key = str(params.get("service_key", "")).strip().lower()
    return get_financial_advisor_payload(service_key)


def _handle_explain_chart(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Wraps get_financial_advisor_payload for a service key."""
    service_key = str(params.get("service_key", "")).strip().lower()
    return get_financial_advisor_payload(service_key)


def _handle_suggest_optimizations(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Wraps PortfolioOptimizerService and OpportunityDetectionService payloads."""
    focus = str(params.get("focus", "all")).strip().lower()
    res: dict[str, Any] = {}
    if focus in ("all", "portfolio", "portfolio_optimizer"):
        res["portfolio_optimizer"] = PortfolioOptimizerService().payload()
    if focus in ("all", "opportunity", "opportunity_detection"):
        res["opportunity_detection"] = OpportunityDetectionService().payload()
    return res
