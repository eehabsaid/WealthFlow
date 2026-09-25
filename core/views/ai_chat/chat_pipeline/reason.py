"""Stage 3 — Reason: the existing first LLM call (initial_generate), unchanged.

Includes its built-in guards (fake-tool-call recovery, one empty-reply nudge).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.services.ai.context_builder_service.constants import DEFAULT_CORE_SERVICES
from core.views.ai_chat.ai_chat_helpers import _aiT_fallback_no_answer, _parse_tool_call

from .retrieve import Retrieval
from .trace import PipelineTrace

_DATA_DOMAIN = "business_data_analysis"
_TOOL_INTENTS = ("action_request", "forecast")  # keep tools: they need more than the injected snapshot


@dataclass
class Reasoning:
    tools_param: Any
    error: str | None
    content: str
    tool_calls: list


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
        if understanding.entities.get("periods"):
            return False, "specific_period"  # month-level detail may not be in the snapshot
    return True, "topical_data_provider_match"


def run_reason(trace: PipelineTrace, provider, messages_seq, question_domain: str,
               retrieval: Retrieval | None = None, understanding=None) -> Reasoning:
    from core.views.ai_chat.ai_chat_core_views import generation_pipeline as gp  # lazy: avoids import cycle

    with trace.stage("reason") as rec:
        grounded, why = answer_from_context(retrieval, question_domain, understanding)
        tools_param, error_str, content_str, tool_calls_req = gp.initial_generate(
            provider, messages_seq, question_domain, offer_tools=not grounded
        )
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
