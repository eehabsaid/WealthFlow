"""show_chart tool: the CHART NUMBERS COME FROM THE DATABASE, never from the model. The model only picks which chart."""

from __future__ import annotations

import datetime
import calendar

from django.db.models import Sum

from core.models import AIChatBlock, Expense, SalaryEntry
from core.services.shared.base_currency import get_user_base_code

CHARTS = ("expenses_by_category", "expenses_by_month", "salary_by_month")


def _year(params: dict) -> int:
    try:
        return int(params.get("year") or datetime.date.today().year)
    except (TypeError, ValueError):
        return datetime.date.today().year


def _expenses_by_category(user, year, month):
    qs = Expense.objects.filter(owner=user, year=year)
    if month:
        qs = qs.filter(month=month)
    rows = qs.values("category__name").annotate(total=Sum("amount_base")).order_by("-total")
    labels = [r["category__name"] or "—" for r in rows]
    values = [float(r["total"] or 0) for r in rows]
    when = f"{year}-{month:02d}" if month else str(year)
    return {"type": "pie", "title": f"Expenses by category {when}", "labels": labels, "series": [{"name": "Expenses", "values": values}]}


def _expenses_by_month(user, year, _month):
    totals = dict(Expense.objects.filter(owner=user, year=year).values_list("month").annotate(t=Sum("amount_base")))
    return {"type": "bar", "title": f"Expenses by month {year}", "labels": [calendar.month_abbr[m] for m in range(1, 13)],
            "series": [{"name": "Expenses", "values": [float(totals.get(m) or 0) for m in range(1, 13)]}]}


def _salary_by_month(user, year, _month):
    order = [calendar.month_name[m] for m in range(1, 13)]
    got = {}
    for e in SalaryEntry.objects.filter(company__owner=user, year=year):
        got[e.month.strip().lower()] = got.get(e.month.strip().lower(), 0) + float(e.paid or 0)
    return {"type": "line", "title": f"Salary paid by month {year}", "labels": [m[:3] for m in order],
            "series": [{"name": "Paid", "values": [got.get(m.lower(), 0.0) for m in order]}]}


_BUILD = {"expenses_by_category": _expenses_by_category, "expenses_by_month": _expenses_by_month, "salary_by_month": _salary_by_month}


def show_chart(user, params: dict) -> dict:
    chart = str(params.get("chart") or "")
    if chart not in _BUILD:
        return {"error": f"`chart` must be one of {list(CHARTS)}"}
    month = params.get("month")
    try:
        month = int(month) if month else None
    except (TypeError, ValueError):
        month = None
    if month is not None and not 1 <= month <= 12:
        return {"error": "`month` must be 1-12"}
    payload = _BUILD[chart](user, _year(params), month)
    if not any(payload["series"][0]["values"]):
        return {"error": "there is no data for that period, so no chart was drawn; tell the user"}
    payload["unit"] = get_user_base_code(user)
    block = AIChatBlock.objects.create(user=user, kind=AIChatBlock.KIND_CHART, status=AIChatBlock.STATUS_READY, payload=payload)
    return {"ok": True, "chart_id": block.id, "title": payload["title"], "labels": payload["labels"], "values": payload["series"][0]["values"],
            "note": "The chart is drawn under your answer from these exact numbers. Describe it in one or two sentences; do not repeat every number."}
