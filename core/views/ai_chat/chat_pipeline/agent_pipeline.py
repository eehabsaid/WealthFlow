"""Agent mode pipeline: the model owns the tool loop from the first call (no instant answer, no normal path first).

Reuses the investigation loop with the agent options: editable instructions, step/time/read limits (Settings > AI
Advisor), a live step list, a Stop flag, an evidence-first rule and Sources built from the tool calls that really ran.
The computed rows for the question (if the router finds any) are only a HINT in the user message.
"""

from __future__ import annotations

from typing import Any, Callable

from core.services.ai.agent import control
from core.services.ai.agent.messages import NO_TOOLS, STOPPED, note
from core.services.ai.agent.settings import limits
from core.services.ai.agent.sources import build_sources
from core.services.ai.investigation import loop as inv_loop
from core.views.ai_chat.ai_chat_helpers import _aiT_fallback_no_answer

from .investigate import _int_setting, _setting
from .trace import PipelineTrace, TracedProvider

CHITCHAT_MAX_WORDS = 2      # "hi" / "thanks": answered without forcing a tool call
HINT_MAX_CHARS = 1500


def _history(conversation, user_msg) -> list:
    rows = conversation.messages.filter(is_deleted=False).exclude(id=user_msg.id).order_by("-id")[:4]
    return [{"role": m.role, "content": m.content} for m in reversed(list(rows))]


def _compose(result, user_text: str) -> str:
    content = result.content
    if result.reason == "cancelled":
        return note(STOPPED, user_text) + (f"\n\n{content}" if content else "")
    if content and not result.steps and not result.native_tools:
        return f"{content}\n\n{note(NO_TOOLS, user_text)}"
    return content


def run_agent_pipeline(*, trace: PipelineTrace, provider, request, conversation, user_msg, user_text: str, hint: str = "",
                       respond: Callable[..., Any], on_error: Callable[[list, str], Any]):
    user, cid = request.user, conversation.id
    for stage in ("route", "knowledge", "retrieve", "prefetch", "reason", "tool", "validate"):
        if stage not in trace.records:
            trace.skip(stage, "agent_mode")
    lim = limits()
    ctx_chars = max(12000, min(80000, _int_setting(user, "ai_context_size", 8192, 2048, 65536) * 3))
    control.clear_stop(user, cid)
    try:
        with trace.stage("investigate") as rec:
            result = inv_loop.investigate(
                TracedProvider(provider, trace), user, user_text, history=_history(conversation, user_msg),
                max_steps=lim["ai_agent_max_steps"], budget_s=lim["ai_agent_budget_s"], ctx_chars=ctx_chars,
                require_evidence=len(user_text.split()) > CHITCHAT_MAX_WORDS, conversation_id=cid,
                extra_refusal_markers=(_aiT_fallback_no_answer(),), agent=True, hint=hint[:HINT_MAX_CHARS],
                max_reads=lim["ai_agent_max_reads"], cancel_check=lambda: control.is_stopped(user, cid))
            rec.detail.update({"why": "agent_mode", "steps": len(result.steps), "tools": [s.get("tool") for s in result.steps],
                               "statuses": [s.get("status") for s in result.steps], "llm_calls": result.llm_calls,
                               "nudges": result.nudges, "reason": result.reason, "error": result.error,
                               "content_chars": len(result.content), "hinted": bool(hint)})
        content = _compose(result, user_text)
        debug = _setting(user, "ai_pipeline_debug", "false") in ("true", "1", "yes")
        extra = {"pipeline": trace.to_dict()} if debug else None
        if content:
            with trace.stage("respond") as rec:
                rec.detail.update({"path": "agent", "content_chars": len(content), "tool_steps": len(result.steps)})
                return respond(content, result.steps, build_sources(result.steps), extra)
        with trace.stage("respond") as rec:
            rec.detail["path"] = "provider_error"
            return on_error(["investigation"], result.error or "The agent produced no answer")
    finally:
        control.clear_stop(user, cid)
        trace.log_summary()
