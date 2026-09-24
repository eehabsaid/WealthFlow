"""Stage 5 — Validate: check the answer against what was actually retrieved.

Cost model (built for ~1-2 tok/s local decoding — see the delivery report):
  1. Skip outright when there is nothing to check (mode off, small talk / app-structure
     questions, empty or fallback answers, no evidence, no checkable figures). ~0 ms.
  2. Otherwise a deterministic, LLM-free grounding pass (grounding.py). ~ms.
  3. Only if figures are NOT grounded does anything expensive happen, and only when
     AppSettings `ai_validate_mode` = "regenerate": ONE extra LLM call, skipped if the
     wall-clock budget can't afford it. Default mode "flag" never makes an LLM call.

ai_validate_mode: "off" | "flag" (default) | "regenerate"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.models import AppSettings
from core.services.ai.cache_manager import AICacheManager
from core.views.ai_chat.ai_chat_helpers import MAX_TOOL_ITERATIONS, _aiT_fallback_no_answer, _get_loop_timeout

from .grounding import GroundingReport, ground_answer
from .retrieve import Retrieval
from .tool import ToolOutcome
from .trace import PipelineTrace
from .understand import Understanding

MODES = ("off", "flag", "regenerate")
_NO_CHECK_INTENTS = ("smalltalk", "app_structure")
_CAVEAT = {
    "en": "\n\n⚠️ Note: I couldn't match these figures to your data: {figs}. Please double-check them before relying on them.",
    "ar": "\n\n⚠️ تنبيه: لم أتمكن من مطابقة هذه الأرقام مع بياناتك: {figs}. يرجى التحقق منها قبل الاعتماد عليها.",
}
_CORRECTION = (
    "VALIDATION: your draft answer contained figures that do not appear in the data or tool results "
    "above: {figs}. Rewrite the answer using ONLY figures present in that data (or a simple sum/difference/"
    "percentage of them, stated briefly). If a figure is not available, say so instead of estimating. "
    "Do not call any tools."
)


@dataclass
class Validation:
    content: str
    verdict: str = "skipped"          # skipped | grounded | flagged | regenerated
    ungrounded: list[str] = field(default_factory=list)
    regenerated: bool = False


def get_mode(user: Any) -> str:
    mode = str(AppSettings.get("ai_validate_mode", "flag", user=user) or "flag").strip().lower()
    return mode if mode in MODES else "flag"


def collect_evidence(messages_seq: list[dict], context_text: str) -> str:
    """Retrieved data + tool results + numbers the user typed. Excludes the system prompt
    and earlier assistant turns (unverified)."""
    parts = [context_text]
    for m in messages_seq[1:]:
        content = str(m.get("content", ""))
        if m.get("role") == "user" or (m.get("role") == "system" and content.startswith("STEP ")):
            parts.append(content)
    return "\n".join(p for p in parts if p)


def _caveat(content: str, figs: list[str], lang: str) -> str:
    text = _CAVEAT.get(lang, _CAVEAT["en"]).format(figs="; ".join(figs[:5]))
    return content.rstrip() + text


def _skip(rec, reason: str, content: str) -> Validation:
    rec.status = "skipped"
    rec.detail["reason"] = reason
    return Validation(content=content)


def _publish_progress(user: Any, conversation_id: Any, steps: int, trace: PipelineTrace) -> None:
    try:
        AICacheManager().set(
            f"ai_loop_progress:{user.id}:{conversation_id}",
            {"step": steps, "max_steps": MAX_TOOL_ITERATIONS, "tool": "validating",
             "label": "Verifying figures against your data...", "status": "running",
             "elapsed_s": round(trace.elapsed_ms() / 1000, 1)},
            ttl_seconds=1800.0,
        )
    except Exception:
        pass  # progress is cosmetic


def _regenerate(provider, messages_seq, report: GroundingReport, user_text: str, evidence: str):
    msgs = list(messages_seq) + [{"role": "system", "content": _CORRECTION.format(figs="; ".join(report.ungrounded[:8]))}]
    res = provider.generate(msgs, tools=None)
    text = str((res or {}).get("content", "") or "").strip() if isinstance(res, dict) else ""
    if not text or (isinstance(res, dict) and res.get("error")):
        return None, None
    return text, ground_answer(text, user_text, evidence)


def run_validate(trace: PipelineTrace, provider, messages_seq: list[dict], retrieval: Retrieval,
                 tool: ToolOutcome, understanding: Understanding, user_text: str, user: Any,
                 conversation_id: Any) -> Validation:
    content = tool.content or ""
    with trace.stage("validate") as rec:
        mode = get_mode(user)
        rec.detail["mode"] = mode
        if mode == "off":
            return _skip(rec, "mode_off", content)
        if understanding.intent in _NO_CHECK_INTENTS:
            return _skip(rec, f"intent_{understanding.intent}", content)
        if not content.strip() or content == _aiT_fallback_no_answer():
            return _skip(rec, "empty_or_fallback_answer", content)
        evidence = collect_evidence(messages_seq, retrieval.context_text)
        if not evidence.strip() or (not retrieval.context_text and not tool.executed):
            return _skip(rec, "no_evidence_to_check_against", content)

        report = ground_answer(content, user_text, evidence)
        rec.detail.update({"checked_figures": report.checked, "methods": report.methods,
                           "evidence_chars": len(evidence)})
        if report.checked == 0:
            return _skip(rec, "no_checkable_figures", content)
        if report.ok:
            rec.detail["verdict"] = "grounded"
            return Validation(content=content, verdict="grounded")

        rec.detail["ungrounded"] = list(report.ungrounded)
        lang = understanding.scope.get("language", "en")
        if mode == "regenerate":
            est_ms = trace.records["reason"].to_dict()["llm_ms"] if "reason" in trace.records else 0
            if trace.elapsed_ms() + est_ms > _get_loop_timeout() * 1000:
                rec.detail["regenerate_skipped"] = "wall_clock_budget"
            else:
                _publish_progress(user, conversation_id, len(tool.executed), trace)
                new_text, new_report = _regenerate(provider, messages_seq, report, user_text, evidence)
                rec.detail["regenerated"] = new_text is not None
                if new_text is not None and len(new_report.ungrounded) < len(report.ungrounded):
                    rec.detail["ungrounded_after"] = list(new_report.ungrounded)
                    if new_report.ok:
                        rec.detail["verdict"] = "regenerated"
                        return Validation(content=new_text, verdict="regenerated", regenerated=True)
                    return Validation(
                        content=_caveat(new_text, list(new_report.ungrounded), lang), verdict="flagged",
                        ungrounded=list(new_report.ungrounded), regenerated=True,
                    )
        rec.detail["verdict"] = "flagged"
        return Validation(content=_caveat(content, list(report.ungrounded), lang), verdict="flagged",
                          ungrounded=list(report.ungrounded))
