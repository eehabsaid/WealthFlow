"""DataAgent — wraps the existing read-only AI tools (already validated via
validate_and_execute_tool's 5 security rules) as an orchestration agent. See
ai/services/orchestration/__init__.py for reachability status."""

from __future__ import annotations

from typing import Any

from ai.services.orchestration.agents.base import BaseAgent
from ai.services.orchestration.state import TaskState
from ai.services.tools.execution import validate_and_execute_tool

_ALLOWED_ACTIONS = (
    "query_application_data",
    "read_live_app_structure",
    "read_application_codebase",
    "suggest_app_feature",
)


class DataAgent(BaseAgent):
    name = "data_agent"

    def available_actions(self) -> list[str]:
        return list(_ALLOWED_ACTIONS)

    def run(self, action: str, params: dict[str, Any], state: TaskState) -> dict[str, Any]:
        if action not in _ALLOWED_ACTIONS:
            return {"ok": False, "error": f"data_agent cannot perform '{action}'"}
        _audit, result = validate_and_execute_tool(action, params, state.owner)
        return result
