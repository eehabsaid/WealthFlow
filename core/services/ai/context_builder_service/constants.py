"""
Constants for AI Context Builder Service — advisor service selection.
"""

from __future__ import annotations

DEFAULT_CORE_SERVICES = ["overview", "cash_flow", "goal_planning", "risk_analysis"]

TOPIC_KEYWORD_MAP: dict[str, list[str]] = {
    "portfolio_optimizer": ["portfolio", "allocation", "rebalance", "diversification", "asset class"],
    "wealth_growth": ["growth", "future wealth", "long term", "projection", "forecast", "compounding"],
    "spending_intelligence": ["spending", "expense", "category", "budget", "trend", "cost", "discretionary"],
    "opportunity_detection": ["opportunity", "idle cash", "yield", "optimize", "savings", "return"],
    "performance": ["performance", "return", "historical", "gain", "loss", "metric"],
    "what_if_simulator": ["what if", "simulate", "simulation", "salary increase", "windfall"],
    "scenario_planner": ["scenario", "recession", "stress test", "crisis", "inflation"],
}


def match_advisor_services_by_name(query_lower: str, available_services: list[str]) -> list[str]:
    """Whole-word match of advisor service names (e.g. "what_if_simulator" ->
    "what", "if", "simulator") against the query. Skips words <=3 chars (e.g.
    "what", "if", "is") — common English words, not distinctive service-name
    terms. A naive substring check here previously let "what" false-match
    what_if_simulator on almost any question phrased as "what is...", pulling
    in that service's full payload as pure noise."""
    import re

    matched: list[str] = []
    for service_key in available_services:
        clean_key = service_key.replace("_", " ").lower()
        terms = [t for t in clean_key.split() if len(t) > 3]
        if terms and any(re.search(rf"\b{re.escape(t)}\b", query_lower) for t in terms):
            matched.append(service_key)
    return matched
