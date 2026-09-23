"""Orchestrator — bounded Decide -> Act -> Observe loop across DataAgent,
AdvisorAgent, ScenarioAgent. See core/services/ai/orchestration/__init__.py
for reachability status (currently unreachable — no view/setting/URL
constructs this).

Decision step reuses the same LLM provider (BaseAIProvider.generate) already
used for normal chat, asking it to choose the next agent+action as JSON.
Parsing reuses _extract_balanced_json from fake_tool_call_recovery.py, since
the local model is already known (confirmed in production) to sometimes
narrate JSON instead of returning clean structured output — see that
module's docstring for the exact failure mode this guards against.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core.services.ai.orchestration.agents import AdvisorAgent, DataAgent, ScenarioAgent
from core.services.ai.orchestration.state import TaskState
from core.views.ai_chat.fake_tool_call_recovery import _extract_balanced_json

logger = logging.getLogger(__name__)

MAX_STEPS = 5

_DECISION_INSTRUCTIONS = (
    "You are the orchestrator for a multi-agent financial assistant. "
    "You have three agents available:\n"
    "- data_agent: {data_actions}\n"
    "- advisor_agent: {advisor_actions}\n"
    "- scenario_agent: {scenario_actions}\n\n"
    "Given the goal and the steps taken so far, decide the single next step, "
    "or declare the goal met. Respond with ONLY a JSON object, no other text:\n"
    '{{"goal_met": false, "agent": "<agent_name>", "action": "<action_name>", '
    '"params": {{...}}}}\n'
    "or, once you have enough information:\n"
    '{{"goal_met": true, "final_answer": "<answer text>"}}'
)


class Orchestrator:
    """Runs the bounded loop. Currently unreachable — nothing in the app
    constructs this outside tests (mocked provider only)."""

    def __init__(self, provider: Any, max_steps: int = MAX_STEPS):
        self.provider = provider
        self.max_steps = max_steps
        self.agents = {
            "data_agent": DataAgent(),
            "advisor_agent": AdvisorAgent(),
            "scenario_agent": ScenarioAgent(),
        }

    def _decision_prompt(self, state: TaskState) -> list[dict[str, str]]:
        instructions = _DECISION_INSTRUCTIONS.format(
            data_actions=", ".join(self.agents["data_agent"].available_actions()),
            advisor_actions=", ".join(self.agents["advisor_agent"].available_actions()),
            scenario_actions=", ".join(self.agents["scenario_agent"].available_actions()),
        )
        return [
            {"role": "system", "content": instructions},
            {"role": "user", "content": f"Goal: {state.goal}\n\nSteps so far:\n{state.to_prompt_summary()}"},
        ]

    def _parse_decision(self, content: str) -> dict[str, Any] | None:
        if not content:
            return None
        for i, ch in enumerate(content):
            if ch != "{":
                continue
            obj_str = _extract_balanced_json(content, i)
            if not obj_str:
                continue
            try:
                obj = json.loads(obj_str)
            except Exception:
                continue
            if isinstance(obj, dict) and "goal_met" in obj:
                return obj
        return None

    def run(self, goal: str, owner: Any) -> TaskState:
        """Runs to completion (goal met, max_steps hit, or an unparsable
        decision) and returns the final TaskState. Never raises."""
        state = TaskState(goal=goal, owner=owner, status="in_progress")

        for _ in range(self.max_steps):
            gen = self.provider.generate(self._decision_prompt(state))
            content = gen.get("content", "") if isinstance(gen, dict) else ""
            decision = self._parse_decision(content)

            if decision is None:
                state.status = "failed"
                state.final_answer = "Orchestrator could not parse a decision from the model."
                return state

            if decision.get("goal_met"):
                state.status = "done"
                state.final_answer = str(decision.get("final_answer", "")).strip() or None
                return state

            agent_name = str(decision.get("agent", "")).strip()
            action = str(decision.get("action", "")).strip()
            params = decision.get("params") or {}
            if not isinstance(params, dict):
                params = {}

            agent = self.agents.get(agent_name)
            if agent is None:
                state.record_step(agent_name or "unknown", action, params, {"ok": False, "error": "unknown agent"})
                continue

            result = agent.run(action, params, state)
            state.record_step(agent.name, action, params, result)

        state.status = "failed"
        state.final_answer = f"Orchestrator did not reach a goal-met decision within {self.max_steps} steps."
        return state
