"""Deterministic expense answers (month total / daily list / category breakdown).

Computed straight from the user's own Expense rows with the same home-currency
conversion as ExpensesDataProvider, so numbers match the rest of the app.
Read-only and owner-scoped. Part of core/services/ai/direct_answers.py.
"""

from __future__ import annotations

import re
from typing import Any

from core.services.ai.period_parser import find_periods

_EXPENSE_RE = re.compile(r"\b(expenses?|spending|spent|spend)\b")
_TOTAL_RE = re.compile(r"\b(total|how much|sum|spent|spending)\b")
_DAILY_RE = re.compile(r"\b(daily|per day|by day|each day|every day|day by day|day-by-day)\b")
_CATEGORY_RE = re.compile(r"\b(by category|per category|categories|category breakdown)\b")
_NOT_SIMPLE_RE = re.compile(
    r"\b(compare|comparison|versus|vs|trend|average|avg|why|forecast|predict|growth|between|and|"
    r"then|also|if|explain|difference|highest|lowest|biggest|largest|smallest|top|most|least|"
    r"budget|save|reduce|cut)\b"
)


def match_expense_intent(text: str) -> tuple[str, tuple[int, int]] | None:
    """('total'|'daily'|'category', (year, month)) for a simple single-month question."""
    q = (text or "").lower().strip()
    if not q or len(q) > 120 or any(ord(ch) >= 0x0590 for ch in q):
        return None
    if not _EXPENSE_RE.search(q) or _NOT_SIMPLE_RE.search(q):
        return None
    periods = find_periods(q)
    if len(periods) != 1:
        return None
    daily, category = bool(_DAILY_RE.search(q)), bool(_CATEGORY_RE.search(q))
    if daily and category:
        return None
    if daily:
        return "daily", periods[0]
    if category:
        return "category", periods[0]
    if _TOTAL_RE.search(q):
        return "total", periods[0]
    return None


def _cell(text: str, limit: int = 40) -> str:
    from core.services.ai.query_engine.executors.common import cell

    return cell(text, limit)


def answer_expenses(user: Any, intent: str, period: tuple[int, int]) -> str:
    """Same text as before the engine migration: rendered by the shared expenses executor."""
    from core.services.ai.query_engine.executors.expenses import run
    from core.services.ai.query_engine.render import render
    from core.services.ai.query_engine.spec import QueryRequest

    group = {"total": "", "daily": "day", "category": "category"}[intent]
    return render(run(user, QueryRequest("expenses", metric="total", group_by=group, periods=[period])))
