"""Explicit Understand -> Retrieve -> Reason -> Tool -> Validate -> Respond pipeline (default chat path).

Understand runs earlier (in the view, before the direct-answer shortcut) and its
result is passed in. Every stage is a separate function in this package that
records itself on the shared PipelineTrace.
"""

from __future__ import annotations

from typing import Any, Callable

from core.models import AppSettings

from .prefetch import run_prefetch
from .reason import run_reason
from .respond import run_respond
from .retrieve import run_retrieve
from .tool import run_tool
from .trace import PipelineTrace, TracedProvider
from .understand import Understanding
from .validate import run_validate


def run_default_pipeline(*, trace: PipelineTrace, understanding: Understanding, provider, request,
                         conversation, user_msg, user_text: str,
                         facts_request: dict | None = None,
                         respond: Callable[..., Any], on_error: Callable[[list, str], Any]):
    """respond(content, executed_tool_calls, sources, extra) and on_error(sources, error_str)
    are supplied by the view so cache/progress handling stays where it was."""
    provider = TracedProvider(provider, trace)
    trace.skip("knowledge", "data_question")  # the knowledge stage belongs to the how/where/should path (workflow.py)
    try:
        retrieval = run_retrieve(trace, request, conversation, user_msg, user_text)
        _attach_facts(trace, retrieval, facts_request, request.user)
        pre = run_prefetch(trace, retrieval, understanding, user_text, request.user)
        reasoning = run_reason(trace, provider, retrieval.messages, understanding.question_domain,
                               retrieval, understanding, prefetched=pre.used)

        if reasoning.error:
            trace.skip("tool", "provider_error")
            trace.skip("validate", "provider_error")
            with trace.stage("respond") as rec:
                rec.detail["path"] = "provider_error"
                return on_error(retrieval.sources, reasoning.error)

        tool = run_tool(trace, provider, retrieval.messages, reasoning, user_text, request.user, conversation.id)
        tool.executed = pre.executed + tool.executed
        validation = run_validate(
            trace, provider, retrieval.messages, retrieval, tool, understanding, user_text,
            request.user, conversation.id,
        )
        debug = str(AppSettings.get("ai_pipeline_debug", "false", user=request.user)).strip().lower() in ("true", "1", "yes")
        extra = {"pipeline": trace.to_dict()} if debug else None
        return run_respond(trace, respond, validation.content, tool.executed, retrieval.sources, extra)
    finally:
        trace.log_summary()


def _attach_facts(trace: PipelineTrace, retrieval, facts_request, user) -> None:
    """Item 5: advice / why / comparison questions get a small block of code-computed facts."""
    if not facts_request:
        return
    from core.services.ai.query_engine import build_facts

    facts = build_facts(user, facts_request)
    trace.records["route"].detail["facts_chars"] = len(facts or "")
    if facts:
        retrieval.messages.append({"role": "system", "content": "STEP 0 — " + facts})
