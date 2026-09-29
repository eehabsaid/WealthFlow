"""Stage 2b — Prefetch: deterministic, LLM-free "proactive tool use" on the default path.

When the question names a month that Retrieve did NOT put in context, the old flow offered tool
schemas (~810 tok prefill) and waited for the model to *decide* to call one (~30 s decode at
1.67 tok/s) plus a second prompt pass. Here the same read-only tool
(query_application_data, unbudgeted providers) is run by code, its result is token-capped by
result_budget and appended as a "STEP 0" system message (Validate's evidence collector already
reads "STEP " messages), and Reason then answers without tool schemas or a tool round trip.
Cost: only the (capped, ~1000 tok) result prefill. Any failure/empty result -> falls back to the old path.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.services.ai.tools import validate_and_execute_tool
from core.services.ai.tools.result_budget import compact_tool_result

from .reason import answer_from_context
from .trace import PipelineTrace

_TOOL = "query_application_data"
_REASONS = ("specific_period",)  # uncovered month(s) only; other "not grounded" reasons keep tools
_MAX_CHARS = 4000  # ~1000 tok ≈ 27 s prefill at 36.9 tok/s; the tool schemas it replaces cost ~22 s


@dataclass
class Prefetch:
    used: bool = False
    executed: list = field(default_factory=list)


def run_prefetch(trace: PipelineTrace, retrieval, understanding, user_text: str, user) -> Prefetch:
    with trace.stage("prefetch") as rec:
        grounded, why = answer_from_context(retrieval, understanding.question_domain, understanding)
        if grounded or why not in _REASONS:
            rec.status = "skipped"
            rec.detail["reason"] = why if not grounded else "already_grounded"
            return Prefetch()
        audit, result = validate_and_execute_tool(_TOOL, {"search_query": user_text}, user)
        audit["step"] = 0
        audit["prefetch"] = True
        ok = audit.get("status") == "success" and isinstance(result, dict) and bool(result)
        rec.detail.update({"tool": _TOOL, "status": audit.get("status"), "duration_ms": audit.get("duration_ms")})
        if not ok:
            rec.status = "skipped"
            rec.detail["reason"] = "prefetch_failed_fallback_to_tools"
            return Prefetch(executed=[audit])
        summary = compact_tool_result(result, max_chars=_MAX_CHARS)
        retrieval.messages.append({
            "role": "system",
            "content": f"STEP 0 — DATA FETCHED FOR THIS QUESTION: '{_TOOL}'\nTOOL EXECUTION RESULT: {summary}\n\n"
                       f"Answer the user's query '{user_text}' using only this data and the context above.",
        })
        rec.detail["result_tokens_est"] = len(summary) // 4
        return Prefetch(used=True, executed=[audit])
