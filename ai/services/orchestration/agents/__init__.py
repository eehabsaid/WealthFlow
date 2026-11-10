"""Umbrella re-exports for the orchestration agents package (200-line file
convention — see ai/services/orchestration/__init__.py)."""

from ai.packs import registry
from ai.services.orchestration.agents.base import BaseAgent
from ai.services.orchestration.agents.data_agent import DataAgent
from ai.services.orchestration.agents.scenario_agent import ScenarioAgent



class _NoAdvisorAgent(BaseAgent):
    """Used when no pack provides an advisor agent."""
    name = "advisor_agent"

    def available_actions(self):
        return []

    def run(self, action, params, state):
        return {"ok": False, "error": "No advisor agent is installed"}


def AdvisorAgent():  # noqa: N802 - kept as a class-like name for callers
    """The host pack's advisor agent (registry.agents["advisor_agent"]) or a no-op one."""
    cls = registry().agents.get("advisor_agent")
    return cls() if cls else _NoAdvisorAgent()


__all__ = ["BaseAgent", "DataAgent", "AdvisorAgent", "ScenarioAgent"]
