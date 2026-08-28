"""
AI Tool Execution — validate_and_execute_tool orchestrator.

NOTE (200-line file convention): part of the core/services/ai/tools/
package. Tool-specific parameter rules live in validation_rules.py. If this
file grows past 200 lines, split it further within this package.
"""

from __future__ import annotations

import datetime
import logging
import time
from typing import Any

from core.models import AppSettings
from core.services.ai.tools.defs import AI_TOOL_REGISTRY
from core.services.ai.tools.validation_rules import _validate_tool_specific_params

logger = logging.getLogger(__name__)


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


    tool_specific_rejection = _validate_tool_specific_params(clean_name, clean_params, timestamp)
    if tool_specific_rejection is not None:
        return tool_specific_rejection

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

    # Global read-only configuration enforcement (evaluated after parameters & auth checks)
    ai_read_only_setting = AppSettings.get("ai_read_only", "true").strip().lower() in ("true", "1", "yes")
    if ai_read_only_setting and not tool_def.get("is_read_only", False):
        audit = {
            "tool": clean_name,
            "timestamp": timestamp,
            "status": "rejected",
            "duration_ms": 0,
            "rejection_reason": "Global AI settings enforce read-only mode.",
            "arguments": clean_params,
        }
        return audit, {"ok": False, "error": "Global AI settings enforce read-only mode."}

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

