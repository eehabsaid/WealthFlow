"""Stage 3 — Reason: the existing first LLM call (initial_generate), unchanged.

Includes its built-in guards (fake-tool-call recovery, one empty-reply nudge).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ai.services.context_builder_service.constants import DEFAULT_CORE_SERVICES
from ai.views.ai_chat.ai_chat_helpers import _aiT_fallback_no_answer, _parse_tool_call
from ai.views.ai_chat.chat_pipeline.domain_gate import guard_text
from ai.views.ai_chat.response_sanitizer import strip_latex, strip_leaked_control_tokens
from ai.views.ai_chat.fake_tool_call_recovery import extract_fake_tool_call
from ai.services.tools.defs import AI_TOOL_REGISTRY

from ai.views.ai_chat.chat_pipeline.coverage import periods_covered
from ai.views.ai_chat.chat_pipeline.retrieve import Retrieval
from ai.views.ai_chat.chat_pipeline.trace import PipelineTrace

_DATA_DOMAIN = "business_data_analysis"
_TOOL_INTENTS = ("action_request", "forecast")  # keep tools: they need more than the injected snapshot
_SENTENCE_END = re.compile(r"[.!?؟۔…][\"'’”)\]]*\s+|\n+")


@dataclass
class Reasoning:
    tools_param: Any
    error: str | None
    content: str
    tool_calls: list


class _VoiceSentenceEmitter:
    def __init__(self, request, question: str, domain: str, evidence: str):
        self.request = request
        self.question = question
        self.domain = domain
        self.evidence = evidence
        self.pending = ""
        self.failed = False

    def __call__(self, text: str) -> None:
        self.pending += text
        while match := _SENTENCE_END.search(self.pending):
            self._publish(self.pending[: match.end()])
            self.pending = self.pending[match.end() :]

    def _block(self) -> None:
        self.pending = ""
        blocker = getattr(self.request, "_voice_stream_blocker", None)
        if callable(blocker):
            blocker()

    def fail(self) -> None:
        self.failed = True
        self._block()
        self.request._voice_stream_failed = True
        failure = getattr(self.request, "_voice_stream_failure", None)
        if callable(failure):
            failure()

    def _publish(self, sentence: str) -> None:
        from ai.views.ai_chat.chat_pipeline.validate import _full_report

        text = sentence.strip()
        if not text:
            return
        if extract_fake_tool_call(text, set(AI_TOOL_REGISTRY)):
            self._block()
            return
        clean = strip_latex(strip_leaked_control_tokens(text, set(AI_TOOL_REGISTRY))).strip()
        if not clean or _full_report(clean, self.question, self.evidence).ungrounded:
            self._block()
            return
        if guard_text(self.domain, clean, self.question, self.evidence) != clean:
            self._block()
            return
        callback = getattr(self.request, "_voice_sentence_callback", None)
        if not callable(callback) or not callback(clean):
            self._block()

    def finish(self) -> None:
        if self.pending and not self.failed:
            self._publish(self.pending)
        self.pending = ""


def answer_from_context(retrieval: Retrieval | None, question_domain: str, understanding=None) -> tuple[bool, str]:
    """(True, reason) when retrieval already grounded the answer, so the tool schemas and the
    forced tool round trip can be skipped. Conservative: anything unclear keeps tools on."""
    if retrieval is None or not retrieval.context_text.strip():
        return False, "no_context"
    if question_domain != _DATA_DOMAIN:
        return False, "domain_not_business_data"
    sources = set(retrieval.sources)
    if not sources or sources <= set(DEFAULT_CORE_SERVICES):
        return False, "no_topical_match"  # empty, or only the generic fallback advisor set
    if understanding is not None:
        if understanding.intent in _TOOL_INTENTS:
            return False, f"intent_{understanding.intent}"
        periods = understanding.entities.get("periods")
        if periods:
            if periods_covered(retrieval.context_text, periods, getattr(understanding, "topics", [])):
                return True, "period_covered_in_context"  # month rows already in snapshot: tools add nothing
            return False, "specific_period"  # month-level detail may not be in the snapshot
    return True, "topical_data_provider_match"


def run_reason(trace: PipelineTrace, provider, messages_seq, question_domain: str,
               retrieval: Retrieval | None = None, understanding=None, prefetched: bool = False,
               request=None) -> Reasoning:
    from ai.views.ai_chat.ai_chat_core_views import generation_pipeline as gp  # lazy: avoids import cycle
    from ai.views.ai_chat.chat_pipeline.validate import collect_evidence, get_mode

    with trace.stage("reason") as rec:
        grounded, why = answer_from_context(retrieval, question_domain, understanding)
        if prefetched:
            grounded, why = True, "prefetched_tool_data"
        emitter = None
        if (
            grounded
            and request is not None
            and callable(getattr(request, "_voice_sentence_callback", None))
            and get_mode(request.user) != "regenerate"
        ):
            emitter = _VoiceSentenceEmitter(
                request,
                str(getattr(request, "_voice_question", "")),
                str(getattr(understanding, "enforced", "")),
                collect_evidence(messages_seq, retrieval.context_text if retrieval else ""),
            )
        tools_param, error_str, content_str, tool_calls_req = gp.initial_generate(
            provider,
            messages_seq,
            question_domain,
            offer_tools=not grounded,
            on_text=emitter,
        )
        if emitter:
            emitter.finish()
        escalated = False
        if grounded and not error_str and not tool_calls_req and content_str == _aiT_fallback_no_answer():
            # Context alone produced nothing usable: fall back to the old tool-enabled call.
            escalated = True
            tools_param, error_str, content_str, tool_calls_req = gp.initial_generate(
                provider, messages_seq, question_domain, offer_tools=True
            )
        rec.detail.update({
            "question_domain": question_domain,
            "answer_from_context": grounded and not escalated,
            "context_decision": why,
            "escalated_to_tools": escalated,
            "tools_offered": len(tools_param or []),
            "requested_tool_calls": [_parse_tool_call(tc)[0] for tc in (tool_calls_req or [])],
            "content_chars": len(content_str or ""),
            "error": error_str,
        })
        return Reasoning(tools_param, error_str, content_str, tool_calls_req)
