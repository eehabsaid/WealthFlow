"""
AI Tool Handler — what_if_scenario (dedicated, parameterized, READ-ONLY).

Exposes WhatIfSimulatorService to the AI agent with explicit hypothetical
inputs (salary / expense changes, gold target, reinvestment choice), optional
multi-scenario comparison, and an optional goal-completion estimate.

READ-ONLY GUARANTEE: only WhatIfSimulatorService.payload() and read-only Goal
queries are called; no model save()/update() is ever invoked.
"""

from __future__ import annotations

import math
from typing import Any

from core.models import Goal
from core.services.financial_advisor.what_if_simulator_service import WhatIfSimulatorService
from core.services.financial_advisor.what_if_simulator_service.helpers import _to_float

SCENARIO_PARAM_KEYS = (
    "salary_change_pct",
    "expenses_change_pct",
    "gold_allocation_target_pct",
    "certificate_reinvestment_choice",
)


def _scenario_params(params: dict[str, Any]) -> dict[str, Any]:
    """Extract the supported hypothetical parameters from one scenario dict."""
    out: dict[str, Any] = {}
    for key in SCENARIO_PARAM_KEYS:
        if key in params and params[key] is not None:
            out[key] = params[key]
    return out


def _has_hypothetical_input(params: dict[str, Any]) -> bool:
    """A scenario must change at least one supported parameter (non-default).

    An explicitly supplied gold_allocation_target_pct (including 0) counts as a
    requested change — only an omitted/None value means 'keep current'."""
    for key in SCENARIO_PARAM_KEYS:
        if key not in params or params[key] is None:
            continue
        if key == "certificate_reinvestment_choice":
            if str(params[key]) != "reinvest":
                return True
        elif key == "gold_allocation_target_pct":
            return True
        else:
            if _to_float(params[key]) != 0.0:
                return True
    return False


def _goal_estimate(owner, goal_name: str) -> dict[str, Any] | None:
    """Months-to-goal estimate from the owner's real goal rows (read-only)."""
    name = str(goal_name or "").strip()
    if not name:
        return None
    goal = Goal.objects.filter(owner=owner, name__iexact=name).first()
    if goal is None:
        return {"goal": name, "found": False}
    target = _to_float(goal.target_amount)
    saved = _to_float(goal.current_saved_amount)
    remaining = max(0.0, target - saved)
    return {
        "goal": name,
        "found": True,
        "target_amount": round(target, 2),
        "current_saved": round(saved, 2),
        "remaining": round(remaining, 2),
    }


def _goal_months(estimate: dict[str, Any] | None, extra_monthly: float) -> int | None:
    """Months to reach the goal saving `extra_monthly` more per month (real remaining / extra)."""
    if not estimate or not estimate.get("found"):
        return None
    extra = _to_float(extra_monthly)
    remaining = _to_float(estimate.get("remaining"))
    if extra <= 0 or remaining <= 0:
        return None
    return math.ceil(remaining / extra)


def _run_scenario(owner, params: dict[str, Any]) -> dict[str, Any]:
    svc = WhatIfSimulatorService(owner)
    payload = svc.payload(**params)
    if payload.get("error"):
        return {"ok": False, "error": payload["error"], "parameters": params}
    return {
        "ok": True,
        "parameters": payload.get("parameters", {}),
        "current_values": payload.get("current_values", {}),
        "baseline": payload.get("baseline", {}),
        "adjusted": payload.get("adjusted", {}),
        "delta": payload.get("delta", {}),
    }


def _goal_estimate_block(params: dict[str, Any], user: Any) -> dict[str, Any] | None:
    """Build the goal_estimate block (None when no goal_name was supplied)."""
    goal_name = str(params.get("goal_name", "")).strip()
    if not goal_name:
        return None
    goal_estimate = _goal_estimate(user, goal_name)
    extra = _to_float(params.get("extra_monthly_savings"))
    if goal_estimate and goal_estimate.get("found"):
        goal_estimate["months_with_extra_savings"] = _goal_months(goal_estimate, extra)
    return goal_estimate


def _handle_what_if_scenario(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Execute one or more hypothetical scenarios and/or a goal estimate.

    A request may carry scenarios, a goal estimate, or both. At least one of
    the two is required; a goal-only request needs no salary/expense override."""
    scenarios = params.get("scenarios")
    if scenarios is not None and not isinstance(scenarios, list):
        return {"ok": False, "error": "Parameter 'scenarios' must be a list"}
    goal_name = str(params.get("goal_name", "")).strip()
    if not scenarios and not goal_name:
        return {
            "ok": False,
            "error": (
                "Provide at least one hypothetical scenario (salary_change_pct, "
                "expenses_change_pct, gold_allocation_target_pct, certificate_reinvestment_choice) "
                "or a goal_name for a goal-completion estimate."
            ),
        }

    results = []
    for idx, sc in enumerate(scenarios or []):
        if not isinstance(sc, dict):
            return {"ok": False, "error": f"Scenario at index {idx} must be an object"}
        sc_params = _scenario_params(sc)
        if not _has_hypothetical_input(sc_params):
            return {
                "ok": False,
                "error": (
                    f"Scenario at index {idx} has no hypothetical change. Provide at least one of: "
                    "salary_change_pct, expenses_change_pct, gold_allocation_target_pct, "
                    "certificate_reinvestment_choice ('cashout')."
                ),
            }
        results.append(_run_scenario(user, sc_params))

    goal_estimate = _goal_estimate_block(params, user)

    if scenarios:
        first_ok = next((r for r in results if r.get("ok")), None)
        if first_ok is None:
            return {"ok": False, "error": "All scenarios failed", "scenarios": results, "goal_estimate": goal_estimate}
        current = first_ok.get("current_values", {})
        if not any(_to_float(current.get(k)) for k in ("monthly_salary", "monthly_expenses")):
            return {
                "ok": False,
                "needs_clarification": True,
                "error": (
                    "No salary or expense records found for this account. Add a salary entry or "
                    "expense records first, then ask the what-if question again."
                ),
                "scenarios": results,
                "goal_estimate": goal_estimate,
            }

    return {
        "ok": True,
        "read_only": True,
        "scenarios": results,
        "goal_estimate": goal_estimate,
    }
