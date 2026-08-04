"""
Centralized AI Financial Advisor Tools Registry and Validation Pipeline.

Provides plain Python tool definitions, Ollama function-calling schemas, handlers,
and a mandatory 5-step validation pipeline before executing any requested tool call.
"""

from __future__ import annotations

import datetime
import logging
import time
from typing import Any

from core.services.financial_advisor.registry import (
    ADVISOR_SERVICE_PROVIDERS,
    get_financial_advisor_payload,
)
from core.services.financial_advisor.scenario_planner_service import (
    ScenarioPlannerService,
    create_scenario_record,
)
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.opportunity_detection_service import OpportunityDetectionService

logger = logging.getLogger(__name__)


# ── Tool Handlers ─────────────────────────────────────────────────────────────

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


# ── Registered Tools Map & Ollama Schemas ─────────────────────────────────────

AI_TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "create_scenario": {
        "name": "create_scenario",
        "description": "Create a new financial scenario with optional events to project future wealth and cash flow impact.",
        "is_read_only": False,
        "handler": _handle_create_scenario,
        "schema": {
            "type": "function",
            "function": {
                "name": "create_scenario",
                "description": "Create a new financial scenario with optional events to project future wealth and cash flow impact.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Scenario name"},
                        "description": {"type": "string", "description": "Scenario description"},
                        "is_baseline_pinned": {"type": "boolean", "description": "Pin as baseline scenario"},
                        "events": {
                            "type": "array",
                            "description": "List of scenario events",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "event_type": {"type": "string", "description": "Type key (house, car, salary_change, marriage, child, retirement, inheritance, medical, business, job_loss)"},
                                    "event_date": {"type": "string", "description": "Event date (YYYY-MM-DD)"},
                                    "params": {"type": "object", "description": "Event specific parameters"},
                                    "order": {"type": "integer", "description": "Display order"}
                                },
                                "required": ["event_type", "event_date"]
                            }
                        }
                    },
                    "required": ["name"]
                }
            }
        }
    },
    "compare_scenarios": {
        "name": "compare_scenarios",
        "description": "Compare financial performance, debt, cash flow, and net worth projections across multiple scenarios by ID.",
        "is_read_only": True,
        "handler": _handle_compare_scenarios,
        "schema": {
            "type": "function",
            "function": {
                "name": "compare_scenarios",
                "description": "Compare financial performance, debt, cash flow, and net worth projections across multiple scenarios by ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scenario_ids": {
                            "type": "array",
                            "description": "List of scenario IDs to compare",
                            "items": {"type": "integer"}
                        }
                    },
                    "required": ["scenario_ids"]
                }
            }
        }
    },
    "summarize_report": {
        "name": "summarize_report",
        "description": "Fetch real data payload for a financial advisor service (e.g. overview, cash_flow, spending_intelligence, risk_analysis) to summarize.",
        "is_read_only": True,
        "handler": _handle_summarize_report,
        "schema": {
            "type": "function",
            "function": {
                "name": "summarize_report",
                "description": "Fetch real data payload for a financial advisor service to summarize.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_key": {
                            "type": "string",
                            "description": "Service key (overview, cash_flow, wealth_growth, portfolio_optimizer, goal_planning, risk_analysis, spending_intelligence, opportunity_detection, performance, what_if_simulator, scenario_planner)"
                        }
                    },
                    "required": ["service_key"]
                }
            }
        }
    },
    "explain_chart": {
        "name": "explain_chart",
        "description": "Fetch real chart/forecast payload data for a service key to explain what the figures and trends mean.",
        "is_read_only": True,
        "handler": _handle_explain_chart,
        "schema": {
            "type": "function",
            "function": {
                "name": "explain_chart",
                "description": "Fetch real chart/forecast payload data for a service key to explain what figures mean.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_key": {
                            "type": "string",
                            "description": "Service key to fetch chart data for"
                        }
                    },
                    "required": ["service_key"]
                }
            }
        }
    },
    "suggest_optimizations": {
        "name": "suggest_optimizations",
        "description": "Fetch real optimization recommendations from Portfolio Optimizer and Opportunity Detection services.",
        "is_read_only": True,
        "handler": _handle_suggest_optimizations,
        "schema": {
            "type": "function",
            "function": {
                "name": "suggest_optimizations",
                "description": "Fetch real optimization recommendations from Portfolio Optimizer and Opportunity Detection services.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "focus": {
                            "type": "string",
                            "description": "Focus area ('all', 'portfolio', or 'opportunity')",
                            "default": "all"
                        }
                    }
                }
            }
        }
    },
}


def get_registered_tool_schemas() -> list[dict[str, Any]]:
    """Returns list of registered tool schemas in Ollama function-calling format."""
    return [t["schema"] for t in AI_TOOL_REGISTRY.values()]


# ── Validation Pipeline & Execution Engine ───────────────────────────────────

def validate_and_execute_tool(
    tool_name: str,
    params: dict[str, Any] | None,
    user: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Validate tool execution request against 5 mandatory security rules in order:
    1. Tool Registry Check: Unknown tool name -> REJECT
    2. Parameters Schema Check: Invalid/missing/wrong-typed params -> REJECT
    3. Authenticated User Check: Anonymous execution -> REJECT
    4. Authorization Check: Active user auth permission -> REJECT
    5. Business Rules Check: Underlying model/service business rule -> REJECT

    Returns (audit_record, tool_result) tuple.
    Audit record contains:
        - tool: str
        - timestamp: str (ISO format)
        - status: "success" | "failed" | "rejected"
        - duration_ms: int
        - rejection_reason: str (optional)
        - arguments: dict
    Must NEVER put raw exception strings or stack traces into audit record.
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clean_name = str(tool_name or "").strip()
    clean_params = params if isinstance(params, dict) else {}

    # Rule 1: Tool Registry Name Check
    if clean_name not in AI_TOOL_REGISTRY:
        audit = {
            "tool": clean_name or "unknown",
            "timestamp": timestamp,
            "status": "rejected",
            "duration_ms": 0,
            "rejection_reason": f"Unknown tool '{clean_name}'",
            "arguments": clean_params,
        }
        return audit, {"ok": False, "error": f"Unknown tool '{clean_name}'"}

    tool_def = AI_TOOL_REGISTRY[clean_name]
    fn_schema = tool_def["schema"]["function"]["parameters"]
    required_fields = fn_schema.get("required", [])

    # Rule 2: Parameters Schema Validation
    for field in required_fields:
        if field not in clean_params or clean_params[field] is None:
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": f"Missing required parameter '{field}'",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": f"Missing required parameter '{field}'"}

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

    # Rule 3: Authenticated User Check
    if not user or not getattr(user, "is_authenticated", False):
        audit = {
            "tool": clean_name,
            "timestamp": timestamp,
            "status": "rejected",
            "duration_ms": 0,
            "rejection_reason": "User authentication required",
            "arguments": clean_params,
        }
        return audit, {"ok": False, "error": "User authentication required"}

    # Rule 4: Authorization Check
    if not getattr(user, "is_active", True):
        audit = {
            "tool": clean_name,
            "timestamp": timestamp,
            "status": "rejected",
            "duration_ms": 0,
            "rejection_reason": "User account is inactive",
            "arguments": clean_params,
        }
        return audit, {"ok": False, "error": "User account is inactive"}

    # Rule 5: Business Rules Validation (e.g. event schema inside create_scenario)
    if clean_name == "create_scenario":
        events = clean_params.get("events") or []
        for idx, ev in enumerate(events):
            if not isinstance(ev, dict):
                audit = {
                    "tool": clean_name,
                    "timestamp": timestamp,
                    "status": "rejected",
                    "duration_ms": 0,
                    "rejection_reason": f"Event at index {idx} must be an object",
                    "arguments": clean_params,
                }
                return audit, {"ok": False, "error": f"Event at index {idx} must be an object"}
            etype = str(ev.get("event_type", "")).strip()
            edate = ev.get("event_date")
            if not etype or not edate:
                audit = {
                    "tool": clean_name,
                    "timestamp": timestamp,
                    "status": "rejected",
                    "duration_ms": 0,
                    "rejection_reason": f"Event at index {idx} missing event_type or event_date",
                    "arguments": clean_params,
                }
                return audit, {"ok": False, "error": f"Event at index {idx} missing event_type or event_date"}

    # Validation passed -> Execute handler with duration tracking
    start_time = time.perf_counter()
    handler = tool_def["handler"]

    try:
        result_data = handler(user=user, params=clean_params)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        audit = {
            "tool": clean_name,
            "timestamp": timestamp,
            "status": "success",
            "duration_ms": elapsed_ms,
            "arguments": clean_params,
        }
        return audit, {"ok": True, "data": result_data}
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning("Tool '%s' execution failed: %s", clean_name, exc, exc_info=True)
        audit = {
            "tool": clean_name,
            "timestamp": timestamp,
            "status": "failed",
            "duration_ms": elapsed_ms,
            "rejection_reason": "Execution error",
            "arguments": clean_params,
        }
        return audit, {"ok": False, "error": "Tool execution failed"}
