"""ScenarioAgent — wraps the scenario/report tool group (create_scenario,
compare_scenarios, summarize_report, explain_chart, suggest_optimizations),
already validated via validate_and_execute_tool. See
core/services/ai/orchestration/__init__.py for reachability status."""

from __future__ import annotations

from typing import Any

from core.services.ai.orchestration.agents.base import BaseAgent
from core.services.ai.orchestration.state import TaskState
from core.services.ai.tools.execution import validate_and_execute_tool

_ALLOWED_ACTIONS = (
    "create_scenario",
    "compare_scenarios",
    "summarize_report",
    "explain_chart",
    "suggest_optimizations",
)


class ScenarioAgent(BaseAgent):
    name = "scenario_agent"

    def available_actions(self) -> list[str]:
        return list(_ALLOWED_ACTIONS)

    def run(self, action: str, params: dict[str, Any], state: TaskState) -> dict[str, Any]:
        if action not in _ALLOWED_ACTIONS:
            return {"ok": False, "error": f"scenario_agent cannot perform '{action}'"}
        _audit, result = validate_and_execute_tool(action, params, state.owner)
        return result
