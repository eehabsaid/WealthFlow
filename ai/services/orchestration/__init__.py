"""
Multi-agent orchestration engine (Decide -> Act -> Observe across DataAgent,
AdvisorAgent, ScenarioAgent, with shared TaskState).

REACHABILITY: gated behind AISetting "ai_multi_agent_enabled" (default
"false"), toggled from the AI Settings page. When on, AIChatView routes each
chat message through Orchestrator.run() instead of the normal single-shot
pipeline — see ai/views/ai_chat/ai_chat_core_views/__init__.py. Bounded to
Orchestrator.MAX_STEPS (5) round trips per request. On this deployment's
measured local decode speed, each round trip costs real wall-clock minutes —
that cost is now the user's explicit choice via the toggle, not a hidden
default.
"""

from ai.services.orchestration.orchestrator import Orchestrator
from ai.services.orchestration.state import TaskState

__all__ = ["Orchestrator", "TaskState"]

