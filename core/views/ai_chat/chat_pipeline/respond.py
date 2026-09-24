"""Stage 6 — Respond: existing finalize_success (persist, knowledge extraction, JSON), unchanged."""

from __future__ import annotations

from typing import Any, Callable

from .trace import PipelineTrace


def run_respond(trace: PipelineTrace, respond: Callable[..., Any], content: str,
                executed: list, sources: list, extra: dict | None = None):
    with trace.stage("respond") as rec:
        rec.detail.update({"content_chars": len(content or ""), "tool_steps": len(executed), "sources": list(sources)})
        return respond(content, executed, sources, extra)
