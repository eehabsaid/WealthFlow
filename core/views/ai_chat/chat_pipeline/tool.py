"""Stage 4 — Tool: the existing bounded investigation loop, unchanged.

The loop is always invoked (it also publishes the 'finalizing' progress state);
the stage is marked 'skipped' when the model asked for no tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.views.ai_chat.ai_chat_loop import run_tool_investigation_loop

from .reason import Reasoning
from .trace import PipelineTrace


@dataclass
class ToolOutcome:
    content: str
    executed: list = field(default_factory=list)


def run_tool(trace: PipelineTrace, provider, messages_seq, reasoning: Reasoning,
             user_text: str, user, conversation_id) -> ToolOutcome:
    with trace.stage("tool") as rec:
        content, executed = run_tool_investigation_loop(
            provider, messages_seq, reasoning.tools_param, reasoning.tool_calls, reasoning.content,
            user_text, user, conversation_id,
        )
        if not executed:
            rec.status = "skipped"
            rec.detail["reason"] = "model requested no tool calls"
        rec.detail.update({
            "steps": len(executed),
            "tools": [e.get("tool") for e in executed],
            "statuses": [e.get("status") for e in executed],
            "content_chars": len(content or ""),
        })
        return ToolOutcome(content=content, executed=executed)
