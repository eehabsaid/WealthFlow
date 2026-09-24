"""Stage 2 — Retrieve: named, inspectable wrapper around the existing context builder.

Logic is unchanged: it calls generation_pipeline.build_context(), which runs
ContextBuilderService.assemble_messages() (business-data grounding with the
semantic bonus, advisor-service matching, token budgeting, history window).
This module only records what came back and keeps the retrieved evidence text
so Validate can check the answer against it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .trace import PipelineTrace

CONTEXT_MARKER = "=== FINANCIAL CONTEXT DATA ==="


@dataclass
class Retrieval:
    messages: list[dict[str, Any]]
    sources: list[str]
    context_text: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def split_context(system_content: str) -> str:
    """The data section of the assembled system message (everything after the marker)."""
    _, _, data = (system_content or "").partition(CONTEXT_MARKER)
    return data.strip()


def run_retrieve(trace: PipelineTrace, request, conversation, user_msg, user_text: str) -> Retrieval:
    from core.views.ai_chat.ai_chat_core_views import generation_pipeline as gp  # lazy: avoids import cycle

    with trace.stage("retrieve") as rec:
        messages, sources = gp.build_context(request, conversation, user_msg, user_text)
        first = messages[0].get("content", "") if messages else ""
        context_text = split_context(first) if messages and messages[0].get("role") == "system" else ""
        rec.detail.update({
            "sources": list(sources),
            "system_chars": len(first),
            "context_chars": len(context_text),
            "context_tokens_est": len(context_text) // 4,
            "history_messages": max(0, len(messages) - 2),
            "empty_context": not context_text,
        })
        return Retrieval(messages=messages, sources=list(sources), context_text=context_text)
