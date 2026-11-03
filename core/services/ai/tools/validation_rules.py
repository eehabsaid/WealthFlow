"""
AI Tool Execution — per-tool parameter validation rules (Rule 2 continued).

NOTE (200-line file convention): part of the core/services/ai/tools/
package — the tool-name-specific parameter checks previously inline in
validate_and_execute_tool. If this file grows past 200 lines, split it
further by tool name within this package.
"""

from __future__ import annotations

from typing import Any

import math

from core.services.ai.tools.rejections import make_rejection
from core.services.financial_advisor.registry import ADVISOR_SERVICE_PROVIDERS


def _finite_number(value) -> float | None:
    """Return the value as a finite float, or None when it is a boolean,
    non-numeric, NaN, or infinite."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if math.isfinite(num) else None


def _validate_tool_specific_params(
    clean_name: str,
    clean_params: dict[str, Any],
    timestamp: str,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """
    Returns an (audit, response) rejection tuple if clean_params fails a
    tool-specific parameter check, otherwise returns None (validation passed).
    """
    if clean_name == "create_scenario":
        name_val = clean_params.get("name")
        if not isinstance(name_val, str) or not name_val.strip():
            return make_rejection(clean_name, timestamp, clean_params, "Parameter 'name' must be a non-empty string")
        if "events" in clean_params and not isinstance(clean_params["events"], list):
            return make_rejection(clean_name, timestamp, clean_params, "Parameter 'events' must be a list")

    elif clean_name == "compare_scenarios":
        scenario_ids = clean_params.get("scenario_ids")
        if not isinstance(scenario_ids, list):
            return make_rejection(clean_name, timestamp, clean_params, "Parameter 'scenario_ids' must be a list of integers")
        for item in scenario_ids:
            if not isinstance(item, int) or isinstance(item, bool):
                return make_rejection(clean_name, timestamp, clean_params, "All elements in 'scenario_ids' must be integers")

    elif clean_name == "what_if_scenario":
        scenarios = clean_params.get("scenarios")
        if scenarios is not None and not isinstance(scenarios, list):
            return make_rejection(clean_name, timestamp, clean_params, "Parameter 'scenarios' must be a list")
        goal_name = str(clean_params.get("goal_name", "")).strip()
        if not scenarios and not goal_name:
            return make_rejection(
                clean_name, timestamp, clean_params,
                "Provide at least one hypothetical scenario or a goal_name for a goal-completion estimate.",
            )
        for idx, sc in enumerate(scenarios or []):
            if not isinstance(sc, dict):
                return make_rejection(clean_name, timestamp, clean_params, f"Scenario at index {idx} must be an object")
            has_change = False
            for k in ("salary_change_pct", "expenses_change_pct", "gold_allocation_target_pct"):
                if k not in sc or sc[k] is None:
                    continue
                val = _finite_number(sc[k])
                if val is None:
                    return make_rejection(clean_name, timestamp, clean_params, f"Scenario at index {idx}: '{k}' must be a finite number")
                if k == "salary_change_pct" and not (-100.0 <= val <= 100.0):
                    return make_rejection(clean_name, timestamp, clean_params, f"Scenario at index {idx}: 'salary_change_pct' must be between -100 and 100")
                if k == "expenses_change_pct" and not (-50.0 <= val <= 100.0):
                    return make_rejection(clean_name, timestamp, clean_params, f"Scenario at index {idx}: 'expenses_change_pct' must be between -50 and 100")
                if k == "gold_allocation_target_pct" and val < 0.0:
                    return make_rejection(clean_name, timestamp, clean_params, f"Scenario at index {idx}: 'gold_allocation_target_pct' must be >= 0")
                if k == "gold_allocation_target_pct" or val != 0.0:
                    has_change = True
            choice = sc.get("certificate_reinvestment_choice")
            if choice is not None:
                choice = str(choice).strip().lower()
                if choice not in ("reinvest", "cashout"):
                    return make_rejection(
                        clean_name, timestamp, clean_params,
                        f"Scenario at index {idx}: 'certificate_reinvestment_choice' must be 'reinvest' or 'cashout'",
                    )
                if choice == "cashout":
                    has_change = True
            if not has_change:
                return make_rejection(
                    clean_name, timestamp, clean_params,
                    f"Scenario at index {idx} has no hypothetical change. Set a non-zero salary_change_pct, "
                    "expenses_change_pct, gold_allocation_target_pct, or certificate_reinvestment_choice='cashout'.",
                )
        extra = clean_params.get("extra_monthly_savings")
        if extra is not None:
            extra_val = _finite_number(extra)
            if extra_val is None:
                return make_rejection(clean_name, timestamp, clean_params, "'extra_monthly_savings' must be a finite number")
            if extra_val < 0:
                return make_rejection(clean_name, timestamp, clean_params, "'extra_monthly_savings' must be >= 0")
        if goal_name and extra is None:
            return make_rejection(
                clean_name, timestamp, clean_params,
                "A goal-completion estimate requires both 'goal_name' and 'extra_monthly_savings'.",
            )
        if goal_name and extra is not None and _finite_number(extra) == 0.0:
            return make_rejection(
                clean_name, timestamp, clean_params,
                "'extra_monthly_savings' must be > 0 for a goal-completion estimate.",
            )

    elif clean_name in ("summarize_report", "explain_chart"):
        skey = str(clean_params.get("service_key", "")).strip().lower()
        if skey not in ADVISOR_SERVICE_PROVIDERS:
            return make_rejection(clean_name, timestamp, clean_params, f"Invalid service_key '{skey}'")

    elif clean_name == "suggest_optimizations":
        focus = str(clean_params.get("focus", "all")).strip().lower()
        if focus not in ("all", "portfolio", "opportunity", "portfolio_optimizer", "opportunity_detection"):
            return make_rejection(clean_name, timestamp, clean_params, f"Invalid focus parameter '{focus}'")

    elif clean_name == "suggest_app_feature":
        focus_area = clean_params.get("focus_area")
        if not isinstance(focus_area, str) or not focus_area.strip():
            return make_rejection(clean_name, timestamp, clean_params, "Parameter 'focus_area' must be a non-empty string")

    elif clean_name == "query_application_data":
        qtype = str(clean_params.get("query_type", "all")).strip().lower()
        if qtype not in ("all", "financial_position", "expense_vs_salary", "asset_net_worth_contribution", "long_term_growth_categories", "exchange_rate_correlation", "cross_module_summary", "net_worth"):
            return make_rejection(clean_name, timestamp, clean_params, f"Invalid query_type parameter '{qtype}'")

    return None
