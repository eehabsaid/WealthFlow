"""Proactive insights: facts about the user's own data, computed by CODE on demand (never written by the model, never stored).
Each insight is {id, type, severity, params}; the page writes the sentence from its translations."""

from __future__ import annotations

import calendar
from datetime import date

from django.db.models import Sum

from core.constants import MONTH_ORDER
from core.models import Expense, SalaryEntry
from core.services.budgets import AlertService
from core.services.shared.base_currency import get_user_base_code

SEVERITY = {"budget_exceeded": "warn", "budget_threshold": "warn", "recurring_overdue": "warn", "salary_unpaid": "warn",
            "recurring_due_soon": "info", "month_vs_last": "info"}


def _budget_and_recurring(user, today):
    for a in AlertService.get_alerts(user, today):
        key = a.get("budget_id") or a.get("recurring_id")
        params = {k: v for k, v in a.items() if k not in ("type",)}
        yield {"id": f"{a['type']}:{key}", "type": a["type"], "severity": SEVERITY.get(a["type"], "info"), "params": params}


def _salary_unpaid(user, today):
    rows = SalaryEntry.objects.filter(company__owner=user, year=today.year, month__iexact=MONTH_ORDER[today.month - 1], paid=0, expected__gt=0)
    for e in rows.select_related("company"):
        yield {"id": f"salary_unpaid:{e.id}", "type": "salary_unpaid", "severity": "warn",
               "params": {"company": e.company.name, "month": e.month, "year": e.year, "expected": float(e.expected)}}


def _month_vs_last(user, today):
    prev_year, prev_month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    day = min(today.day, calendar.monthrange(prev_year, prev_month)[1])

    def total(y, m, last_day):
        return Expense.objects.filter(owner=user, year=y, month=m, date__day__lte=last_day).aggregate(t=Sum("amount_base"))["t"] or 0

    now, before = float(total(today.year, today.month, today.day)), float(total(prev_year, prev_month, day))
    if before <= 0:
        return
    yield {"id": "month_vs_last", "type": "month_vs_last", "severity": "info",
           "params": {"this_month": round(now, 2), "last_month": round(before, 2), "change_percent": round((now - before) / before * 100, 1),
                      "through_day": today.day, "currency": get_user_base_code(user)}}


def compute_insights(user, today: date | None = None) -> list[dict]:
    today = today or date.today()
    found = [*_budget_and_recurring(user, today), *_salary_unpaid(user, today), *_month_vs_last(user, today)]
    return sorted(found, key=lambda i: 0 if i["severity"] == "warn" else 1)
