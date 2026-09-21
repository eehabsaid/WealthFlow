"""
Deterministic salary answers for query_application_data.

Small local models misread long lists and yearly totals, so the answer for
"latest salary" and for "salary of <Month> <Year>" is computed here and placed
first in the 'salary' payload. The month lookup queries the database directly,
so it also works for months outside the capped recent_monthly_timeline window.

NOTE (200-line file convention): part of the core/services/ai/tools/ package.
"""

from __future__ import annotations

from typing import Any

SALARY_INSTRUCTIONS = (
    " SALARY RULE: for a 'latest'/'last'/'most recent' paid salary, or a specific month, use ONLY "
    "salary.requested_period_answer or salary.latest_paid_salary_answer when present (quote it verbatim), "
    "otherwise salary.latest_salary_entry (report its 'paid_formatted', year, month and company). "
    "The 'salary' key has no 'recent_salary' list and the generic list-index-0 rule does not "
    "apply to it; never treat a missing 'recent_salary' as 'no salary data'. Do not use "
    "recent_monthly_timeline (oldest-first) or latest_active_year_summary (yearly aggregate) "
    "for this; a yearly total is never a single paid salary. Only say no salary data exists if "
    "latest_salary_entry is null/absent."
)

_LATEST_WORDS = ("last", "latest", "recent", "newest", "current")
_MONTHS = ["january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december"]


def _parse_month_year(query: str) -> tuple[int, int] | None:
    from core.services.ai.period_parser import find_periods

    periods = find_periods(query)
    return (periods[0][1], periods[0][0]) if periods else None  # (month, year)


def _month_answer(user: Any, month: int, year: int) -> str:
    from core.models import SalaryEntry
    from core.services.ai.providers.salary_provider.constants import MONTH_NAME_TO_INT
    from core.services.ai.providers.salary_provider.provider import SalaryDataProvider

    provider = SalaryDataProvider()
    currency = provider.get_user_primary_currency(user)
    qs = SalaryEntry.objects.filter(company__owner=user, year=year).select_related("company")
    rows = [e for e in qs if MONTH_NAME_TO_INT.get(str(e.month or "").strip().lower()) == month]
    label = f"{_MONTHS[month - 1].capitalize()} {year}"
    if not rows:
        return f"No salary entry is recorded for {label}."
    parts = [
        f"{provider.format_currency(float(e.paid or 0), currency)} from {e.company.name if e.company else ''}"
        for e in rows
    ]
    return f"Paid salary for {label}: " + "; ".join(parts) + "."


def add_salary_answers(res: dict[str, Any], user: Any, search_query: str) -> None:
    """Put ready-made answers first inside res['salary'] (copies the dict; never mutates a cached one)."""
    salary = res.get("salary")
    if not isinstance(salary, dict):
        return
    q = str(search_query or "").lower()
    extra: dict[str, str] = {}
    period = _parse_month_year(q)
    if period and user is not None and getattr(user, "is_authenticated", False):
        extra["requested_period_answer"] = _month_answer(user, *period)
    latest = salary.get("latest_salary_entry")
    if latest and any(w in q for w in _LATEST_WORDS):
        extra["latest_paid_salary_answer"] = (
            f"Latest paid salary: {latest.get('paid_formatted')} for "
            f"{latest.get('month')} {latest.get('year')} from {latest.get('company')}."
        )
    if extra:
        res["salary"] = {**extra, **salary}
