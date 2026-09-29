"""Deterministic multi-month expense tables: per-month rows, a total row after each month and a
grand total row — computed from Expense rows, zero LLM calls.

Why: "detailed expenses table for Jun..Sept with totals" made the local model decode hundreds of
table tokens at ~1.7 tok/s (many minutes) and hand-add totals it often gets wrong. Same
home-currency conversion as ExpensesDataProvider (amount_base). Part of direct_answers.py.
"""

from __future__ import annotations

import calendar
import re
from typing import Any

from core.services.ai.expense_direct import _cell, _load, match_expense_intent
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


def _bold_row(cols: list[str]) -> str:
    return "| " + " | ".join(f"**{c}**" if c else "" for c in cols) + " |"


def answer_expense_table(user: Any, mode: str, periods: list[tuple[int, int]]) -> str:
    grand, grand_n, lines = 0.0, 0, []
    provider, home = None, None
    if mode == "category":
        header = ["| Month | Category | Transactions | Amount |", "|---|---|---|---|"]
    else:
        header = ["| Month | Date | Category | Description | Amount |", "|---|---|---|---|---|"]
    empty = []
    for year, month in periods:
        label = f"{calendar.month_abbr[month]} {year}"
        provider, home, rows = _load(user, year, month)
        fmt = lambda v: provider.format_currency(round(v, 2), home)  # noqa: E731
        total = sum(v for _, v in rows)
        grand += total
        grand_n += len(rows)
        if not rows:
            empty.append(label)
        if mode == "category":
            cats: dict[str, list] = {}
            for e, v in rows:
                c = cats.setdefault(e.category.name if e.category else "Uncategorized", [0.0, 0])
                c[0] += v
                c[1] += 1
            for name, (amt, n) in sorted(cats.items(), key=lambda x: x[1][0], reverse=True):
                lines.append(f"| {label} | {_cell(name)} | {n} | {fmt(amt)} |")
            lines.append(_bold_row([f"Total {label}", "", str(len(rows)), fmt(total)]))
        else:
            for e, v in rows:
                cat = e.category.name if e.category else "Uncategorized"
                desc = _cell(e.description or getattr(e, "notes", "") or "", 50)
                lines.append(f"| {label} | {e.date.isoformat() if e.date else ''} | {_cell(cat)} | {desc} | {fmt(v)} |")
            lines.append(_bold_row([f"Total {label}", "", "", "", fmt(total)]))
    if provider is None:
        return "No months were specified."
    fmt = lambda v: provider.format_currency(round(v, 2), home)  # noqa: E731
    if mode == "category":
        lines.append(_bold_row(["Grand Total", "", str(grand_n), fmt(grand)]))
    else:
        lines.append(_bold_row(["Grand Total", "", "", "", fmt(grand)]))
    intro = f"Expenses for {', '.join(f'{calendar.month_abbr[m]} {y}' for y, m in periods)} ({grand_n} transactions, amounts in {home}):"
    note = f"\n\nNo expenses are recorded for: {', '.join(empty)}." if empty else ""
    return "\n".join([intro, "", *header, *lines]) + note
