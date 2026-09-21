"""Deterministic expense answers (month total / daily list / category breakdown).

Computed straight from the user's own Expense rows with the same home-currency
conversion as ExpensesDataProvider, so numbers match the rest of the app.
Read-only and owner-scoped. Part of core/services/ai/direct_answers.py.
"""

from __future__ import annotations

import calendar
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
    text = " ".join(str(text or "").replace("|", "/").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _load(user: Any, year: int, month: int):
    from core.models import Expense
    from core.services.ai.providers.expenses_provider import ExpensesDataProvider

    provider = ExpensesDataProvider()
    home = provider.get_user_primary_currency(user)
    qs = Expense.objects.filter(owner=user, year=year, month=month).select_related("category").order_by("date", "id")
    rows = []
    for e in qs:
        egp = float(e.amount_egp or 0)
        rows.append((e, egp if home == "EGP" else provider.convert_to_home_currency(egp, "EGP", home)))
    return provider, home, rows


def answer_expenses(user: Any, intent: str, period: tuple[int, int]) -> str:
    year, month = period
    label = f"{calendar.month_name[month]} {year}"
    provider, home, rows = _load(user, year, month)
    if not rows:
        return f"No expenses are recorded for {label}."
    fmt = lambda v: provider.format_currency(round(v, 2), home)  # noqa: E731
    total = sum(v for _, v in rows)
    head = f"{fmt(total)} across {len(rows)} transactions"
    if intent == "total":
        return f"Total expenses for {label}: {head}."

    if intent == "daily":
        days: dict[str, list] = {}
        for e, v in rows:
            days.setdefault(e.date.isoformat() if e.date else "No date", []).append((e, v))
        lines = [f"Daily expenses for {label} (total {head}):", "", "| Date | Total | Details |", "|---|---|---|"]
        for day, items in days.items():
            details = "; ".join(
                f"{_cell((e.category.name if e.category else 'Uncategorized') + (': ' + e.description if e.description else ''))} {v:,.2f}"
                for e, v in items
            )
            lines.append(f"| {day} | {fmt(sum(v for _, v in items))} | {details} |")
        return "\n".join(lines)

    cats: dict[str, list[float]] = {}
    for e, v in rows:
        c = cats.setdefault(e.category.name if e.category else "Uncategorized", [0.0, 0])
        c[0] += v
        c[1] += 1
    lines = [f"Expenses by category for {label} (total {head}):", "", "| Category | Total | Share | Transactions |", "|---|---|---|---|"]
    for name, (amt, n) in sorted(cats.items(), key=lambda x: x[1][0], reverse=True):
        share = amt / total * 100 if total else 0.0
        lines.append(f"| {_cell(name)} | {fmt(amt)} | {share:.1f}% | {n} |")
    return "\n".join(lines)
