"""
ORM aggregation phases for the salary data provider: all-time totals,
per-company breakdown, and the dynamic yearly summary with YoY growth.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Avg, Count, QuerySet, Sum


def compute_totals(qs: QuerySet) -> dict[str, Any]:
    sal_agg = qs.aggregate(
        total_paid=Sum("paid"),
        total_expected=Sum("expected"),
        total_bonus=Sum("bonus"),
        avg_paid=Avg("paid"),
        count=Count("id"),
    )
    return {
        "total_paid": float(sal_agg["total_paid"] or 0),
        "total_expected": float(sal_agg["total_expected"] or 0),
        "total_bonus": float(sal_agg["total_bonus"] or 0),
        "total_count": sal_agg["count"] or 0,
        "avg_monthly_paid": float(sal_agg["avg_paid"] or 0),
    }


def compute_company_breakdown(qs: QuerySet, currency_code: str, format_currency) -> list[dict[str, Any]]:
    company_raw = list(
        qs.values("company__name")
        .annotate(
            total_paid=Sum("paid"),
            total_expected=Sum("expected"),
            total_bonus=Sum("bonus"),
            count=Count("id")
        )
        .order_by("-total_paid")
    )
    return [
        {
            "company": c["company__name"] or "Unknown",
            "total_paid": float(c["total_paid"] or 0),
            "total_paid_formatted": format_currency(float(c["total_paid"] or 0), currency_code),
            "total_expected": float(c["total_expected"] or 0),
            "total_expected_formatted": format_currency(float(c["total_expected"] or 0), currency_code),
            "total_bonus": float(c["total_bonus"] or 0),
            "total_bonus_formatted": format_currency(float(c["total_bonus"] or 0), currency_code),
            "entries_count": c["count"],
            "currency": currency_code,
        }
        for c in company_raw
    ]


def compute_yearly_summary(qs: QuerySet, currency_code: str, format_currency) -> dict[str, Any]:
    """Dynamic yearly summary & YoY growth calculation (chronological)."""
    yearly_raw = list(
        qs.values("year")
        .annotate(
            total_paid=Sum("paid"),
            total_expected=Sum("expected"),
            total_bonus=Sum("bonus"),
            count=Count("id")
        )
        .order_by("year")
    )

    yearly_summary = []
    prev_paid = None
    latest_active_year_summary = None
    latest_active_year = max((y["year"] for y in yearly_raw), default=None)

    for y in yearly_raw:
        y_paid = float(y["total_paid"] or 0)
        y_exp = float(y["total_expected"] or 0)
        y_bon = float(y["total_bonus"] or 0)
        yoy_growth_pct = None
        if prev_paid and prev_paid > 0:
            yoy_growth_pct = round(((y_paid - prev_paid) / prev_paid) * 100.0, 2)
        prev_paid = y_paid

        y_item = {
            "year": y["year"],
            "total_paid": y_paid,
            "total_paid_formatted": format_currency(y_paid, currency_code),
            "total_expected": y_exp,
            "total_expected_formatted": format_currency(y_exp, currency_code),
            "total_bonus": y_bon,
            "total_bonus_formatted": format_currency(y_bon, currency_code),
            "entries_count": y["count"],
            "yoy_growth_pct": yoy_growth_pct,
            "currency": currency_code,
        }
        yearly_summary.append(y_item)

        if latest_active_year and y["year"] == latest_active_year:
            latest_active_year_summary = y_item

    return {
        "yearly_summary": yearly_summary,
        "latest_active_year": latest_active_year,
        "latest_active_year_summary": latest_active_year_summary,
    }
