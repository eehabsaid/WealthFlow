"""Centralized configuration + shared numeric helper for ScenarioPlannerService.

NOTE (200-line file convention): extracted from the original monolithic
core/services/financial_advisor/scenario_planner_service.py (716 lines).
See __init__.py for the full package layout.
"""
from __future__ import annotations


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


# ── Centralized Financial Configuration ───────────────────────────────────────
SCENARIO_PLANNER_CONFIG = {
    "EMERGENCY_FUND_MIN_MONTHS": 3.0,
    "EMERGENCY_FUND_TARGET_MONTHS": 6.0,
    "GOAL_PROBABILITY_DROP_THRESHOLD_PCT": 10.0,
    "DEFAULT_RETIREMENT_AGE": 60,
    "DEFAULT_WITHDRAWAL_RATE": 0.04,
    "NEST_EGG_MULTIPLIER": 25.0,  # 1.0 / 0.04
    "DEBT_TO_INCOME_HIGH_THRESHOLD_PCT": 40.0,
}
