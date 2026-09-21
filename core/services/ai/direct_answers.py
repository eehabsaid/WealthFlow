"""Direct answers: questions the code can answer exactly, with zero LLM calls.

Local models spend minutes re-reading ~10K tokens of context just to quote a
value the backend already computed. When a question is a single, unambiguous
fact, the answer is computed from the same deterministic data the LLM would
have been told to quote verbatim:
  - salary: paid salary for one month, or the latest paid salary
    (see tools/salary_answers.py)
  - expenses: total, daily list, or category breakdown for one month
    (see expense_direct.py)

Anything ambiguous, multi-part, comparative or non-English returns None and the
normal LLM pipeline runs unchanged. Kill-switch: AppSettings ai_direct_answers=false.
"""

from __future__ import annotations

import re
import time
from typing import Any

from core.services.ai.period_parser import find_periods

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
    periods = find_periods(q)
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
    return _try_salary(user, text) or _try_expenses(user, text)


def _audit(tool: str, text: str, started: float) -> dict[str, Any]:
    from datetime import datetime, timezone

    return {
        "tool": tool, "timestamp": datetime.now(timezone.utc).isoformat(), "status": "success",
        "duration_ms": int((time.monotonic() - started) * 1000),
        "arguments": {"search_query": text}, "step": 1, "direct_answer": True,
    }


def _try_expenses(user: Any, text: str) -> dict[str, Any] | None:
    from core.services.ai.expense_direct import answer_expenses, match_expense_intent

    intent = match_expense_intent(text)
    if not intent:
        return None
    started = time.monotonic()
    answer = answer_expenses(user, *intent)
    return {"content": answer, "tool_calls": [_audit("direct_answer_expenses", text, started)], "sources": ["expenses"]}


def _try_salary(user: Any, text: str) -> dict[str, Any] | None:
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
