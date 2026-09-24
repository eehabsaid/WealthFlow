"""Stage 3 — Reason: the existing first LLM call (initial_generate), unchanged.

Includes its built-in guards (fake-tool-call recovery, one empty-reply nudge).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.views.ai_chat.ai_chat_helpers import _parse_tool_call

from .trace import PipelineTrace


@dataclass
class Reasoning:
    tools_param: Any
    error: str | None
    content: str
    tool_calls: list


def run_reason(trace: PipelineTrace, provider, messages_seq, question_domain: str) -> Reasoning:
    from core.views.ai_chat.ai_chat_core_views import generation_pipeline as gp  # lazy: avoids import cycle

    with trace.stage("reason") as rec:
        tools_param, error_str, content_str, tool_calls_req = gp.initial_generate(
            provider, messages_seq, question_domain
        )
        rec.detail.update({
            "question_domain": question_domain,
            "tools_offered": len(tools_param or []),
            "requested_tool_calls": [_parse_tool_call(tc)[0] for tc in (tool_calls_req or [])],
            "content_chars": len(content_str or ""),
            "error": error_str,
        })
        return Reasoning(tools_param, error_str, content_str, tool_calls_req)
