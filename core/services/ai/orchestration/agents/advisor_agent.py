"""AdvisorAgent — wraps the financial_advisor service registry (overview,
cash_flow, goal_planning, risk_analysis, etc.) as an orchestration agent. See
core/services/ai/orchestration/__init__.py for reachability status."""

from __future__ import annotations

from typing import Any

from core.services.ai.orchestration.agents.base import BaseAgent
from core.services.ai.orchestration.state import TaskState
from core.services.financial_advisor.registry import (
    get_available_advisor_services,
    get_financial_advisor_payload,
)


class AdvisorAgent(BaseAgent):
    name = "advisor_agent"

    def available_actions(self) -> list[str]:
        return get_available_advisor_services()

    def run(self, action: str, params: dict[str, Any], state: TaskState) -> dict[str, Any]:
        if action not in self.available_actions():
            return {"ok": False, "error": f"advisor_agent cannot perform '{action}'"}
        payload = get_financial_advisor_payload(action, state.owner)
        return {"ok": True, "data": payload}
