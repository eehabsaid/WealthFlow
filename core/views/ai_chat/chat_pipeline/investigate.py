"""Investigator path: the local model explores the whole app (code, the user's data, docs) with read-only tools.

Used in three situations, all traced as the `investigate` stage:
  * mode "always"                      every question not answered deterministically
  * code questions (sysadmin)          "which file / how is X implemented" go straight here, with evidence required
  * escalation (mode "auto", default)  the normal path gave up ("I don't have ...", empty, provider error) ->
                                       the investigator takes over so the user never gets a "no tools / no data" reply

Settings (AppSettings): ai_investigator_mode auto|always|off, ai_investigator_max_steps (10), ai_investigator_budget_s (240),
ai_code_access (sysadmin source-code tools, default on).
"""

from __future__ import annotations

import re
from typing import Any, Callable

from core.models import AppSettings
from core.services.ai.investigation import loop as inv_loop
from core.services.ai.investigation.defs import CODE_TOOLS
from core.services.ai.investigation.code_tools import code_access_allowed
from core.services.ai.investigation.refusal import is_refusal
from core.views.ai_chat.ai_chat_helpers import _aiT_fallback_no_answer

from .trace import PipelineTrace, TracedProvider

MODES = ("auto", "always", "off")
ESCALATE = object()                      # sentinel returned by an intercepted respond/on_error
KEEP_SOURCES = ("knowledge_fallback",)   # retrieval-only fallback of the workflow path: not worth a second model run
_CODE_HINT = re.compile(
    r"(\.py\b|\.js\b|\.html\b|\bsource code\b|\bcodebase\b|\bwhich file\b|\bwhere in the code\b|\b(?:is|are) (?:it )?implemented\b|"
    r"\bimplementation\b|\bstack ?trace\b|\btraceback\b|\bendpoint\b|\bmigration\b|\bunit tests?\b|\bgit\b|\brepo(?:sitory)?\b|"
    r"\bdef \w+|\bclass \w+|\bfunction\b|الكود|ملف|دالة|الدالة|دوال|الكلاس|البرمجي|"
    r"code source|quel fichier|fonction|classe|implémenté|quellcode|quelltext|welche datei|funktion|klasse|implementiert)", re.I)


def _setting(user, key: str, default: str) -> str:
    return str(AppSettings.get(key, default, user=user) or default).strip().lower()


def investigator_mode(user) -> str:
    mode = _setting(user, "ai_investigator_mode", "auto")
    return mode if mode in MODES else "auto"


def _int_setting(user, key: str, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(_setting(user, key, str(default)))))
    except ValueError:
        return default


def is_code_question(user, text: str) -> bool:
    return code_access_allowed(user) and bool(_CODE_HINT.search(text or ""))


_DOCUMENT_FORMATS = ("xlsx", "docx", "pdf", "csv", "txt")


def wants_data_file(text: str) -> bool:
    """A document/spreadsheet file is requested (code files are just the model's answer, no investigation needed)."""
    from core.services.ai.exports import requested

    return any(f.key in _DOCUMENT_FORMATS for f in requested(text))


def wants_written_document(text: str) -> bool:
    """Word / PDF / text file requested: the file must contain a document (see investigation/compose.py)."""
    from core.services.ai.exports import requested

    return any(f.key in ("docx", "pdf", "txt") for f in requested(text))


def ensure_document(provider, user_text: str, result, ctx_chars: int, user=None) -> bool:
    """Replace a stub answer ("Let me write it...") by the complete document. True when the content was replaced."""
    from core.services.ai.investigation.compose import compose_document, needs_document

    if result.reason == "cancelled" or not wants_written_document(user_text) or not needs_document(result):
        return False
    doc = compose_document(provider, user_text, result, ctx_chars, user)
    if doc:
        result.content = doc
    return bool(doc)


def should_go_direct(user, text: str, *, computed: bool = False) -> str | None:
    """Reason to skip the normal paths and investigate straight away, or None. `computed`: the instant-answer router
    already holds the exact rows for this question (the model gets them as verified data), so no exploration is needed."""
    mode = investigator_mode(user)
    if mode == "off":
        return None
    if mode == "always":
        return "mode_always"
    if is_code_question(user, text):
        return "code_question"
    # "list ... and export it": the capped context is not enough for a complete file; the investigator has generate_file
    return "export_request" if not computed and wants_data_file(text) else None


def answer_failed(content: str, executed: list, sources: list) -> bool:
    """True when a finished normal-path answer is a give-up that the investigator should replace."""
    if list(sources or []) and all(s in KEEP_SOURCES for s in sources):
        return False
    return is_refusal(content, investigated=bool(executed), extra_markers=(_aiT_fallback_no_answer(),))


def escalating(user, respond: Callable[..., Any], on_error: Callable[..., Any]):
    """(respond, on_error, box) wrappers for a normal path. A give-up answer or provider error is held back and the
    sentinel ESCALATE returned instead; box records why. Disabled (pass-through) unless mode is "auto"."""
    box: dict[str, Any] = {}
    if investigator_mode(user) != "auto":
        return respond, on_error, box

    def _respond(content, calls, sources, extra=None):
        if answer_failed(content, calls, sources):
            box["why"] = "refusal"
            return ESCALATE
        return respond(content, calls, sources, extra)

    def _on_error(sources, err):
        box.update(why="provider_error", error=str(err))
        return ESCALATE

    return _respond, _on_error, box


def _source_keys(steps: list) -> list[str]:
    tools = {s.get("tool", "") for s in steps}
    keys = []
    if tools & set(CODE_TOOLS):
        keys.append("investigation_code")
    if tools & {"app_data_models", "app_data_query"}:
        keys.append("investigation_data")
    if "app_knowledge_search" in tools:
        keys.append("investigation_docs")
    return keys or ["investigation"]


def run_investigator_pipeline(*, trace: PipelineTrace, provider, request, conversation, user_msg, user_text: str,
                              respond: Callable[..., Any], on_error: Callable[[list, str], Any], why: str):
    user = request.user
    trace.records.pop("respond", None)   # an escalated normal path already "responded" (intercepted): keep the trace truthful
    for stage in ("knowledge", "retrieve", "prefetch", "reason", "tool", "validate"):
        if stage not in trace.records:
            trace.skip(stage, "investigator_path")
    history = [{"role": m.role, "content": m.content}
               for m in reversed(list(conversation.messages.filter(is_deleted=False).exclude(id=user_msg.id).order_by("-id")[:4]))]
    ctx_chars = max(12000, min(80000, _int_setting(user, "ai_context_size", 8192, 2048, 65536) * 3))
    try:
        with trace.stage("investigate") as rec:
            result = inv_loop.investigate(
                TracedProvider(provider, trace), user, user_text, history=history,
                max_steps=_int_setting(user, "ai_investigator_max_steps", 10, 2, 25),
                budget_s=_int_setting(user, "ai_investigator_budget_s", 240, 40, 1800),
                ctx_chars=ctx_chars, require_evidence=(why == "code_question"), conversation_id=conversation.id,
                extra_refusal_markers=(_aiT_fallback_no_answer(),))
            composed = ensure_document(TracedProvider(provider, trace), user_text, result, ctx_chars, user)
            rec.detail.update({"why": why, "composed_document": composed, "steps": len(result.steps), "tools": [s.get("tool") for s in result.steps],
                               "statuses": [s.get("status") for s in result.steps], "llm_calls": result.llm_calls,
                               "nudges": result.nudges, "reason": result.reason, "error": result.error,
                               "content_chars": len(result.content)})
        debug = _setting(user, "ai_pipeline_debug", "false") in ("true", "1", "yes")
        extra = {"pipeline": trace.to_dict()} if debug else None
        if result.content:
            with trace.stage("respond") as rec:
                rec.detail.update({"path": "investigator", "content_chars": len(result.content), "tool_steps": len(result.steps)})
                return respond(result.content, result.steps, _source_keys(result.steps), extra)
        with trace.stage("respond") as rec:
            rec.detail["path"] = "provider_error"
            return on_error(["investigation"], result.error or "The investigator produced no answer")
    finally:
        trace.log_summary()
