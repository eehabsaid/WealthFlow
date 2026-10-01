"""Direct answers: questions the code can answer exactly, with zero LLM calls.

Since the query-engine migration this module is a thin entry point: every direct answer (salary for
a month / latest, expense total / daily / category / multi-month table, and the new balance, certificates,
fixed assets, gold price by karat and exchange-rate answers, en + ar) is a capability entry in
core/services/ai/query_engine/ (see engine.answer). Kill-switch: AppSettings ai_direct_answers=false.

`_match_salary` is kept importable (its regression tests still guard the wording rules the engine's
router replaced); expense_direct.match_expense_intent / expense_table_direct.match_expense_table_intent
are kept for the same reason.
"""

from __future__ import annotations

import re
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


def try_direct_answer(user: Any, text: str, *, provider: Any = None, understanding: Any = None,
                      info: dict[str, Any] | None = None, elapsed_ms: int = 0, previous: str = "") -> dict[str, Any] | None:
    """Return {content, tool_calls, sources} for a question the engine can answer, else None.
    `info` (optional dict) is filled with the routing decision for the [AI-PIPELINE] trace."""
    from core.services.ai.query_engine import answer

    return answer(user, text, provider=provider, understanding=understanding, info=info, elapsed_ms=elapsed_ms, previous=previous)
