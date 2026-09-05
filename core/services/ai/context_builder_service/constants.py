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
