"""
Multi-agent orchestration engine (Decide -> Act -> Observe across DataAgent,
AdvisorAgent, ScenarioAgent, with shared TaskState).

REACHABILITY: intentionally NOT wired into any view, URL, setting, or the
normal chat pipeline (generation_pipeline.py). Nothing in the app currently
constructs Orchestrator or calls run() — built ahead of the hardware needed
to run it well (see chat history: measured local decode speed makes
multi-round-trip loops impractical on this deployment today). Exists so the
engine can be wired in later with a settings flag + a call site, not another
build. Covered by core/tests/ai/test_orchestration.py with a mocked provider
only — never exercised against a live model.
"""

from core.services.ai.orchestration.orchestrator import Orchestrator
from core.services.ai.orchestration.state import TaskState

__all__ = ["Orchestrator", "TaskState"]
