"""
AI Tool Execution — per-tool parameter validation rules (Rule 2 continued).

NOTE (200-line file convention): part of the core/services/ai/tools/
package — the tool-name-specific parameter checks previously inline in
validate_and_execute_tool. If this file grows past 200 lines, split it
further by tool name within this package.
"""

from __future__ import annotations

from typing import Any

from core.services.financial_advisor.registry import ADVISOR_SERVICE_PROVIDERS


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
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": "Parameter 'name' must be a non-empty string",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": "Parameter 'name' must be a non-empty string"}
        if "events" in clean_params and not isinstance(clean_params["events"], list):
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": "Parameter 'events' must be a list",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": "Parameter 'events' must be a list"}

    elif clean_name == "compare_scenarios":
        scenario_ids = clean_params.get("scenario_ids")
        if not isinstance(scenario_ids, list):
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": "Parameter 'scenario_ids' must be a list of integers",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": "Parameter 'scenario_ids' must be a list of integers"}
        for item in scenario_ids:
            if not isinstance(item, int) or isinstance(item, bool):
                audit = {
                    "tool": clean_name,
                    "timestamp": timestamp,
                    "status": "rejected",
                    "duration_ms": 0,
                    "rejection_reason": "All elements in 'scenario_ids' must be integers",
                    "arguments": clean_params,
                }
                return audit, {"ok": False, "error": "All elements in 'scenario_ids' must be integers"}

    elif clean_name in ("summarize_report", "explain_chart"):
        skey = str(clean_params.get("service_key", "")).strip().lower()
        if skey not in ADVISOR_SERVICE_PROVIDERS:
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": f"Invalid service_key '{skey}'",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": f"Invalid service_key '{skey}'"}

    elif clean_name == "suggest_optimizations":
        focus = str(clean_params.get("focus", "all")).strip().lower()
        if focus not in ("all", "portfolio", "opportunity", "portfolio_optimizer", "opportunity_detection"):
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": f"Invalid focus parameter '{focus}'",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": f"Invalid focus parameter '{focus}'"}

    elif clean_name == "suggest_app_feature":
        focus_area = clean_params.get("focus_area")
        if not isinstance(focus_area, str) or not focus_area.strip():
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": "Parameter 'focus_area' must be a non-empty string",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": "Parameter 'focus_area' must be a non-empty string"}

    elif clean_name == "query_application_data":
        qtype = str(clean_params.get("query_type", "all")).strip().lower()
        if qtype not in ("all", "financial_position", "expense_vs_salary", "asset_net_worth_contribution", "long_term_growth_categories", "exchange_rate_correlation", "cross_module_summary", "net_worth"):
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": f"Invalid query_type parameter '{qtype}'",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": f"Invalid query_type parameter '{qtype}'"}

    return None
