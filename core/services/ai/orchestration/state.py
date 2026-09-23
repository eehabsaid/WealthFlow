"""Shared task state for the multi-agent orchestration engine. See
core/services/ai/orchestration/__init__.py for reachability status
(currently unreachable — no view/setting/URL constructs this package)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskState:
    goal: str
    owner: Any
    steps: list[dict[str, Any]] = field(default_factory=list)
    scratchpad: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending | in_progress | done | failed
    final_answer: str | None = None

    def record_step(self, agent_name: str, action: str, params: dict[str, Any], result: Any) -> None:
        self.steps.append({
            "agent": agent_name,
            "action": action,
            "params": params,
            "result": result,
        })

    def to_prompt_summary(self, max_result_chars: int = 600) -> str:
        """Compact, LLM-readable summary of steps taken so far, fed back into
        the next decision call so the orchestrator doesn't repeat itself."""
        if not self.steps:
            return "(no steps taken yet)"
        lines = []
        for i, step in enumerate(self.steps, start=1):
            result_str = str(step["result"])
            if len(result_str) > max_result_chars:
                result_str = result_str[:max_result_chars] + "... (truncated)"
            lines.append(f"{i}. [{step['agent']}] {step['action']}({step['params']}) -> {result_str}")
        return "\n".join(lines)
