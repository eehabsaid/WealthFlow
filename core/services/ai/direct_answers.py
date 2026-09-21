"""Direct answers: questions the code can answer exactly, with zero LLM calls.

Local models spend minutes re-reading ~10K tokens of context just to quote a
value the backend already computed. When a question is a single, unambiguous
fact (currently: paid salary for one month, or the latest paid salary), the
answer comes from the same deterministic tool payload the LLM would have been
told to quote verbatim (see tools/salary_answers.py).

Anything ambiguous, multi-part, comparative or non-English returns None and the
normal LLM pipeline runs unchanged. Kill-switch: AppSettings ai_direct_answers=false.
"""

from __future__ import annotations

import re
from typing import Any

from core.services.ai.tools.salary_answers import _MONTH_RE

_MAX_LEN = 120
_SALARY_RE = re.compile(r"\b(salary|salaries|paid|payslip)\b")
_LATEST_RE = re.compile(r"\b(last|latest|most recent|newest)\b")
# Words that make a question multi-part or about something other than one paid amount.
_NOT_SIMPLE_RE = re.compile(
    r"\b(compare|comparison|versus|vs|trend|average|avg|total|sum|why|forecast|predict|growth|"
    r"between|history|list|all|every|each|and|then|also|if|explain|tax|deduct\w*|bonus|"
    r"expected|difference|raise|increase|company|companies)\b"
)


def _is_english(text: str) -> bool:
    return all(ord(ch) < 0x0590 for ch in text)


def _match_salary(text: str) -> str | None:
    """Return the salary payload key that answers `text`, or None if not a simple question."""
    q = (text or "").lower().strip()
    if not q or len(q) > _MAX_LEN or not _is_english(q):
        return None
    if not _SALARY_RE.search(q) or _NOT_SIMPLE_RE.search(q):
        return None
    periods = _MONTH_RE.findall(q)
    if len(periods) == 1:
        return "requested_period_answer"
    if not periods and _LATEST_RE.search(q):
        return "latest_paid_salary_answer"
    return None


def try_direct_answer(user: Any, text: str) -> dict[str, Any] | None:
    """Return {content, tool_calls, sources} for a simple deterministic question, else None."""
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    from core.models import AppSettings

    if str(AppSettings.get("ai_direct_answers", "true", user=user)).strip().lower() == "false":
        return None
    key = _match_salary(text)
    if not key:
        return None

    from core.services.ai.tools import validate_and_execute_tool

    audit, res = validate_and_execute_tool("query_application_data", {"search_query": text}, user)
    if not isinstance(res, dict) or audit.get("status") != "success":
        return None
    salary = (res.get("data") or {}).get("salary")
    answer = salary.get(key) if isinstance(salary, dict) else None
    if not isinstance(answer, str) or not answer.strip():
        return None
    audit["step"] = 1
    audit["direct_answer"] = True
    return {"content": answer.strip(), "tool_calls": [audit], "sources": ["salary"]}
