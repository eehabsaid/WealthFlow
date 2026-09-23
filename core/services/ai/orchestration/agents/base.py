"""Base class for orchestration agents. See
core/services/ai/orchestration/__init__.py for reachability status."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.services.ai.orchestration.state import TaskState


class BaseAgent(ABC):
    name: str = "base_agent"

    @abstractmethod
    def available_actions(self) -> list[str]:
        """List of action names this agent can execute."""

    @abstractmethod
    def run(self, action: str, params: dict[str, Any], state: TaskState) -> dict[str, Any]:
        """
        Execute one action. Must never raise — catch and return
        {"ok": False, "error": "..."} on failure, matching
        validate_and_execute_tool's tool_result shape.
        """
