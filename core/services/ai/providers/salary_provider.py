"""
Salary Data Provider for AI business context. Read-only.
Enforces multi-tenant scoping, deterministic ORM aggregation, currency conversion, and career growth analytics.
"""

from __future__ import annotations

from typing import Any
from django.db.models import Sum, Count, Avg
from core.models import SalaryEntry, Company
from core.services.ai.providers.base import BaseContextProvider
# Caps how many entries are included in the AI-facing 'recent_monthly_timeline' list
# when the caller does not pass an explicit `limit`. Aggregates (summary, yearly_summary,
# company_breakdown) are always computed over the FULL queryset regardless of this cap —
# only the per-row timeline list is capped, to keep the JSON payload small enough to
# reliably fit in the model's context window without truncation.
MAX_TIMELINE_ENTRIES_FOR_AI = 20

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
            "inputs": ["user"],
            "outputs": [
                "latest_active_year",
                "latest_active_year_summary",
                "recent_monthly_timeline",
                "summary",
                "yearly_summary",
                "company_breakdown"
            ],
            "description": "Calculates historical, expected, and bonus salary income, career & YTD growth trends, pre-formatted currency metrics, and company breakdowns deterministically.",
        }]

    def get_data(self, user: Any, limit: int | None = None) -> dict[str, Any]:
        currency_code = self.get_user_primary_currency(user)

        # 1. User Scoping
        qs = SalaryEntry.objects.all()
        if user and user.is_authenticated:
            if hasattr(SalaryEntry, "user"):
                qs = qs.filter(user=user)
            elif hasattr(Company, "user"):
                qs = qs.filter(company__user=user)

        # 2. Complete ORM Aggregation
        sal_agg = qs.aggregate(
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

        # 3. Company Breakdown Aggregation
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
        company_breakdown = [
            {
                "company": c["company__name"] or "Unknown",
                "total_paid": float(c["total_paid"] or 0),
                "total_paid_formatted": self.format_currency(float(c["total_paid"] or 0), currency_code),
                "total_expected": float(c["total_expected"] or 0),
                "total_expected_formatted": self.format_currency(float(c["total_expected"] or 0), currency_code),
                "total_bonus": float(c["total_bonus"] or 0),
                "total_bonus_formatted": self.format_currency(float(c["total_bonus"] or 0), currency_code),
                "entries_count": c["count"],
                "currency": currency_code,
            }
            for c in company_raw
        ]

        # 4. Dynamic Yearly Summary & YoY Growth Calculation (Chronological)
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
                "total_paid_formatted": self.format_currency(y_paid, currency_code),
                "total_expected": y_exp,
                "total_expected_formatted": self.format_currency(y_exp, currency_code),
                "total_bonus": y_bon,
                "total_bonus_formatted": self.format_currency(y_bon, currency_code),
                "entries_count": y["count"],
                "yoy_growth_pct": yoy_growth_pct,
                "currency": currency_code,
            }
            yearly_summary.append(y_item)

            if latest_active_year and y["year"] == latest_active_year:
                latest_active_year_summary = y_item

        # 5. Chronological Entry Analysis (Earliest -> Latest)
        all_entries_asc = list(qs.select_related("company").all())
        all_entries_asc.sort(key=_month_sort_key)

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

        career_overall_growth_pct = None
        if first_historical_paid and first_historical_paid > 0 and latest_historical_paid is not None:
            career_overall_growth_pct = round(
                ((latest_historical_paid - first_historical_paid) / first_historical_paid) * 100.0, 2
            )

        paid_consistency_pct = (
            round((paid_consistent_count / total_count) * 100.0, 1)
            if total_count > 0 else 100.0
        )

                # 6. Timeline Entry Assembly (chronological, oldest -> newest)
        all_entries_desc = list(all_entries_asc)
        all_entries_desc.reverse()

        if limit is not None and limit > 0:
            timeline_entries = all_entries_desc[:limit]
        else:
            timeline_entries = all_entries_desc[:MAX_TIMELINE_ENTRIES_FOR_AI]
        timeline_entries.sort(key=_month_sort_key)

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
                "paid_formatted": self.format_currency(p_val, currency_code),
                "expected": e_val,
                "expected_formatted": self.format_currency(e_val, currency_code),
                "bonus": b_val,
                "bonus_formatted": self.format_currency(b_val, currency_code),
                "remaining": entry.remaining,
                "remaining_formatted": self.format_currency(entry.remaining, currency_code),
                "currency": currency_code,
                "notes": entry.notes or "",
            })

        # The single most recent salary entry (by year+month), as an unambiguous
        # standalone object — NOT an aggregate. This is the correct field to answer
        # "what is the latest paid salary" — do not use yearly_summary/company_breakdown
        # (those are SUMS across many entries) or scan recent_monthly_timeline for this.
        latest_salary_entry = None
        if all_entries_asc:
            latest_entry_obj = all_entries_asc[-1]
            latest_salary_entry = {
                "year": latest_entry_obj.year,
                "month": latest_entry_obj.month,
                "company": latest_entry_obj.company.name if latest_entry_obj.company else "",
                "paid": float(latest_entry_obj.paid or 0),
                "paid_formatted": self.format_currency(float(latest_entry_obj.paid or 0), currency_code),
                "expected": float(latest_entry_obj.expected or 0),
                "expected_formatted": self.format_currency(float(latest_entry_obj.expected or 0), currency_code),
                "bonus": float(latest_entry_obj.bonus or 0),
                "bonus_formatted": self.format_currency(float(latest_entry_obj.bonus or 0), currency_code),
            }

        return {
            "currency": currency_code,
            "latest_active_year": latest_active_year,
            "latest_active_year_summary": latest_active_year_summary,
            "latest_active_year_summary_note": (
                "latest_active_year_summary is a YEARLY AGGREGATE (sum of total_paid across all "
                "months in the most recent year) — it is NOT the most recent single paid salary "
                "amount. Do not use it to answer 'what is the latest paid salary'."
            ),
            "latest_salary_entry": latest_salary_entry,
            "latest_salary_entry_note": (
                "latest_salary_entry is the single most recent individual salary entry (one "
                "specific year+month+company), already identified for you. THIS is the correct "
                "field to answer any 'latest/most recent paid salary' question — use its 'paid' "
                "value exactly as given. Do not compute, sum, or infer this value from "
                "recent_monthly_timeline, yearly_summary, or company_breakdown."
            ),
            "recent_monthly_timeline": recent_monthly_timeline,
            "recent_monthly_timeline_note": (
                f"recent_monthly_timeline is capped to at most {MAX_TIMELINE_ENTRIES_FOR_AI} entries "
                f"(out of {total_count} total salary entries on record) when no explicit limit is given, "
                f"sorted chronologically OLDEST-FIRST (ascending) — the LAST item in this list is the "
                f"most recent, not the first. summary, yearly_summary, and company_breakdown above are "
                f"still computed over ALL entries, not just this list. For the single most recent "
                f"salary entry, use the separate 'latest_salary_entry' field instead of scanning this "
                f"list."
            ),
            "summary": {
                "total_paid_all_time": total_paid,
                "total_paid_all_time_formatted": self.format_currency(total_paid, currency_code),
                "total_expected_all_time": total_expected,
                "total_expected_all_time_formatted": self.format_currency(total_expected, currency_code),
                "total_bonus_all_time": total_bonus,
                "total_bonus_all_time_formatted": self.format_currency(total_bonus, currency_code),
                "total_entries_count": total_count,
                "average_monthly_paid": round(avg_monthly_paid, 2),
                "average_monthly_paid_formatted": self.format_currency(round(avg_monthly_paid, 2), currency_code),
                "career_overall_growth_pct": career_overall_growth_pct,
                "paid_consistency_pct": paid_consistency_pct,
                "currency": currency_code,
                "company_breakdown": company_breakdown,
            },
            "yearly_summary": yearly_summary,
        }