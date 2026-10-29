"""Stores one finished Agent run as an AgentTrace. Called from the Agent pipeline; never raises into the chat."""

from __future__ import annotations

import logging

from . import context
from .textutil import script_of

logger = logging.getLogger("core.ai.pipeline")


def enabled() -> bool:
    """Recording is on inside the runner (context) or when the sysadmin setting `ai_trace_recording` is true (real chats)."""
    from core.models import AppSettings

    return context.current() is not None or str(AppSettings.get("ai_trace_recording", "false", user=None) or "").lower() in ("true", "1", "yes")


def record(user, user_text: str, hint: str, result, *, provider=None, domain: str = ""):
    """`result` is the finished investigation (steps, results = [(tool, args, text)], content, reason, elapsed_s)."""
    if not enabled():
        return None
    try:
        from ai_training.models import AgentTrace
        from core.services.ai.investigation import prompt
        from core.services.ai.investigation.defs import investigation_tool_schemas

        schemas = investigation_tool_schemas(user, domain)
        ctx = context.current() or {}
        trace = AgentTrace.objects.create(
            owner=user, source=ctx.get("source") or AgentTrace.SOURCE_CHAT, case_key=ctx.get("case_key", ""), attempt=ctx.get("attempt", 1),
            question=user_text, hint=hint or "", language=script_of(user_text), model_name=str(getattr(provider, "model", "") or ""),
            system_prompt=prompt.build_agent_prompt(user, schemas, bool(result.native_tools), None, domain), tools=schemas,
            steps=[{"tool": t, "arguments": a, "result": r} for t, a, r in result.results], answer=result.content or "",
            reason=result.reason, expected=ctx.get("expected"), elapsed_s=round(result.elapsed_s or 0, 1))
        if ctx:
            ctx["saved"].append(trace.pk)
        return trace
    except Exception:   # recording must never break a chat answer
        logger.exception("[AI-TRACE] could not record the run")
        return None
