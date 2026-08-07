"""
Salary Data Provider for AI business context. Read-only.
Provides complete analytical data, dynamic latest-active-year prioritization,
token-budget driven timeline degradation, exact ORM aggregations,
career & YTD growth analytics, pre-formatted currency strings, and implementation-agnostic scalability.
"""

from __future__ import annotations

from typing import Any
from django.db.models import Sum, Count, Avg
from core.models import SalaryEntry, AppSettings
from core.services.ai.providers.base import BaseContextProvider

MONTH_NAME_TO_INT = {
    "january": 1, "jan": 1, "1": 1, "01": 1,
    "february": 2, "feb": 2, "2": 2, "02": 2,
    "march": 3, "mar": 3, "3": 3, "03": 3,
    "april": 4, "apr": 4, "4": 4, "04": 4,
    "may": 5, "5": 5, "05": 5,
    "june": 6, "jun": 6, "6": 6, "06": 6,
    "july": 7, "jul": 7, "7": 7, "07": 7,
    "august": 8, "aug": 8, "8": 8, "08": 8,
    "september": 9, "sep": 9, "sept": 9, "9": 9, "09": 9,
    "october": 10, "oct": 10, "10": 10,
    "november": 11, "nov": 11, "11": 11,
    "december": 12, "dec": 12, "12": 12,
}


def _month_sort_key(entry: SalaryEntry) -> tuple[int, int]:
    m_val = str(entry.month or "").strip().lower()
    m_idx = MONTH_NAME_TO_INT.get(m_val, 99)
    return (entry.year, m_idx)


def _format_curr(val: float, currency_code: str) -> str:
    return f"{val:,.2f} {currency_code}"


class SalaryDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "salary"

    @property
    def name(self) -> str:
        return "Salary & Income Analytics"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Salary & Income Analytics",
            "provided_by": "SalaryDataProvider",
            "consumes": ["SalaryEntry", "Company", "Currency"],
            "used_by": ["Financial Advisor", "Cash Flow Forecast", "AI Advisor"],
            "inputs": ["year", "month", "company_id"],
            "outputs": [
                "latest_active_year",
                "latest_active_year_summary",
                "recent_monthly_timeline",
                "summary",
                "yearly_summary",
                "company_breakdown"
            ],
            "description": "Calculates historical, expected, and bonus salary income, career & YTD growth trends, monthly timelines, pre-formatted currency metrics, and company breakdowns.",
        }]

    def get_data(self, user: Any, limit: int = 100) -> dict[str, Any]:
        # 1. Resolve primary currency code
        currency_code = "EGP"
        if user and hasattr(user, "profile") and getattr(user.profile, "preferred_currency", None):
            pref_curr = getattr(user.profile, "preferred_currency")
            if hasattr(pref_curr, "code"):
                currency_code = str(pref_curr.code).strip()
            elif pref_curr:
                currency_code = str(pref_curr).strip()
        else:
            currency_code = AppSettings.get("home_currency", "EGP")

        # 2. Complete ORM Aggregation over 100% of records
        sal_agg = SalaryEntry.objects.aggregate(
            total_paid=Sum("paid"),
            total_expected=Sum("expected"),
            total_bonus=Sum("bonus"),
            avg_paid=Avg("paid"),
            count=Count("id"),
        )

        total_paid = float(sal_agg["total_paid"] or 0)
        total_expected = float(sal_agg["total_expected"] or 0)
        total_bonus = float(sal_agg["total_bonus"] or 0)
        total_count = sal_agg["count"] or 0
        avg_monthly_paid = float(sal_agg["avg_paid"] or 0)

        # 3. Company Breakdown Aggregation with Pre-Formatted Strings
        company_raw = list(
            SalaryEntry.objects.values("company__name")
            .annotate(
                total_paid=Sum("paid"),
                total_expected=Sum("expected"),
                total_bonus=Sum("bonus"),
                count=Count("id")
            )
            .order_by("-total_paid")
        )
        company_breakdown = [
            {
                "company": c["company__name"],
                "total_paid": float(c["total_paid"] or 0),
                "total_paid_formatted": _format_curr(float(c["total_paid"] or 0), currency_code),
                "total_expected": float(c["total_expected"] or 0),
                "total_expected_formatted": _format_curr(float(c["total_expected"] or 0), currency_code),
                "total_bonus": float(c["total_bonus"] or 0),
                "total_bonus_formatted": _format_curr(float(c["total_bonus"] or 0), currency_code),
                "entries_count": c["count"],
                "currency": currency_code,
            }
            for c in company_raw
        ]

        # 4. Dynamic Yearly Summary & YoY Growth Calculation (Chronological 2008 -> latest)
        yearly_raw = list(
            SalaryEntry.objects.values("year")
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
                "total_paid_formatted": _format_curr(y_paid, currency_code),
                "total_expected": y_exp,
                "total_expected_formatted": _format_curr(y_exp, currency_code),
                "total_bonus": y_bon,
                "total_bonus_formatted": _format_curr(y_bon, currency_code),
                "entries_count": y["count"],
                "yoy_growth_pct": yoy_growth_pct,
                "currency": currency_code,
            }
            yearly_summary.append(y_item)

            if latest_active_year and y["year"] == latest_active_year:
                latest_active_year_summary = y_item

        # 5. Chronological Entry Analysis (Chronological order: earliest -> latest)
        all_entries_asc = list(SalaryEntry.objects.select_related("company").all())
        all_entries_asc.sort(key=_month_sort_key)  # 2008 -> 2026

        first_historical_paid = None
        latest_historical_paid = None
        paid_consistent_count = 0

        for entry in all_entries_asc:
            p_val = float(entry.paid or 0)
            e_val = float(entry.expected or 0)
            if first_historical_paid is None and p_val > 0:
                first_historical_paid = p_val
            if p_val > 0:
                latest_historical_paid = p_val
                if p_val >= e_val:
                    paid_consistent_count += 1

        # Correct Career Overall Growth % (from first entry 2008 to latest entry 2026)
        career_overall_growth_pct = None
        if first_historical_paid and first_historical_paid > 0 and latest_historical_paid is not None:
            career_overall_growth_pct = round(
                ((latest_historical_paid - first_historical_paid) / first_historical_paid) * 100.0, 2
            )

        paid_consistency_pct = (
            round((paid_consistent_count / total_count) * 100.0, 1)
            if total_count > 0 else 100.0
        )

        # 6. Dynamic Token Budget-Driven Timeline Degradation
        budget_limit = max(12, min(limit, 36))
        all_entries_desc = list(all_entries_asc)
        all_entries_desc.reverse()  # Newest entries FIRST!

        timeline_entries = all_entries_desc[:budget_limit]
        timeline_entries.sort(key=_month_sort_key)  # Chronological order for recent timeline

        recent_monthly_timeline = []
        for entry in timeline_entries:
            p_val = float(entry.paid or 0)
            e_val = float(entry.expected or 0)
            b_val = float(entry.bonus or 0)
            recent_monthly_timeline.append({
                "year": entry.year,
                "month": entry.month,
                "company": entry.company.name if entry.company else "",
                "paid": p_val,
                "paid_formatted": _format_curr(p_val, currency_code),
                "expected": e_val,
                "expected_formatted": _format_curr(e_val, currency_code),
                "bonus": b_val,
                "bonus_formatted": _format_curr(b_val, currency_code),
                "remaining": entry.remaining,
                "remaining_formatted": _format_curr(entry.remaining, currency_code),
                "currency": currency_code,
                "notes": entry.notes or "",
            })

        return {
            "currency": currency_code,
            "latest_active_year": latest_active_year,
            "latest_active_year_summary": latest_active_year_summary,
            "recent_monthly_timeline": recent_monthly_timeline,
            "summary": {
                "total_paid_all_time": total_paid,
                "total_paid_all_time_formatted": _format_curr(total_paid, currency_code),
                "total_expected_all_time": total_expected,
                "total_expected_all_time_formatted": _format_curr(total_expected, currency_code),
                "total_bonus_all_time": total_bonus,
                "total_bonus_all_time_formatted": _format_curr(total_bonus, currency_code),
                "total_entries_count": total_count,
                "average_monthly_paid": round(avg_monthly_paid, 2),
                "average_monthly_paid_formatted": _format_curr(round(avg_monthly_paid, 2), currency_code),
                "career_overall_growth_pct": career_overall_growth_pct,
                "paid_consistency_pct": paid_consistency_pct,
                "currency": currency_code,
                "company_breakdown": company_breakdown,
            },
            "yearly_summary": yearly_summary,
        }
