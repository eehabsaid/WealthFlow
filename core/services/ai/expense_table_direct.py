"""Deterministic multi-month expense tables: per-month rows, a total row after each month and a
grand total row — computed from Expense rows, zero LLM calls.

Why: "detailed expenses table for Jun..Sept with totals" made the local model decode hundreds of
table tokens at ~1.7 tok/s (many minutes) and hand-add totals it often gets wrong. Same
home-currency conversion as ExpensesDataProvider (amount_base). Part of direct_answers.py.
"""

from __future__ import annotations

import re
from typing import Any

from core.services.ai.expense_direct import match_expense_intent
from core.services.ai.period_parser import find_periods

_MAX_LEN = 600
_MAX_MONTHS = 12
_EXPENSE_RE = re.compile(r"\b(expenses?|spending|spent)\b")
_TABLE_RE = re.compile(r"\b(table|tabular|detail(?:s|ed)?|breakdown|organi[sz]ed|list)\b")
_CATEGORY_RE = re.compile(r"\b(by category|per category|categories|category)\b")
# Analysis/advice words: those need the model, so the normal pipeline runs.
_ANALYSIS_RE = re.compile(
    r"\b(compare|comparison|versus|vs|trend|average|avg|why|forecast|predict|growth|explain|"
    r"difference|highest|lowest|biggest|largest|budget|save|reduce|cut|advice|advise|recommend\w*|"
    r"insights?|analy[sz]e|analysis|improve|should|reason)\b"
)


def match_expense_table_intent(text: str) -> tuple[str, list[tuple[int, int]]] | None:
    """('transactions'|'category', [(year, month), ...]) for a pure 'give me the table' request."""
    q = (text or "").lower().strip()
    if not q or len(q) > _MAX_LEN or any(ord(ch) >= 0x0590 for ch in q):
        return None
    if not _EXPENSE_RE.search(q) or not _TABLE_RE.search(q) or _ANALYSIS_RE.search(q):
        return None
    if match_expense_intent(q):
        return None  # simple single-month total/daily/category questions keep their existing exact answers
    periods = sorted(set(find_periods(q)))
    if not periods or len(periods) > _MAX_MONTHS:
        return None
    return ("category" if _CATEGORY_RE.search(q) else "transactions"), periods


def answer_expense_table(user: Any, mode: str, periods: list[tuple[int, int]]) -> str:
    """Same text as before the engine migration: rendered by the shared expenses executor."""
    from core.services.ai.query_engine.executors.expenses import run
    from core.services.ai.query_engine.render import render
    from core.services.ai.query_engine.spec import QueryRequest

    if not periods:
        return "No months were specified."
    group = "category" if mode == "category" else ""
    return render(run(user, QueryRequest("expenses", metric="list", group_by=group, periods=sorted(set(periods)))))
