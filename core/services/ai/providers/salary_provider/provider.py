"""
Salary Data Provider for AI business context. Read-only.
Enforces multi-tenant scoping, deterministic ORM aggregation, currency conversion, and career growth analytics.
"""

from __future__ import annotations

from typing import Any

from core.models import Company, SalaryEntry
from core.services.ai.providers.base import BaseContextProvider
from core.services.ai.providers.salary_provider.aggregation import (
    compute_company_breakdown,
    compute_totals,
    compute_yearly_summary,
)
from core.services.ai.providers.salary_provider.constants import MAX_TIMELINE_ENTRIES_FOR_AI
from core.services.ai.providers.salary_provider.timeline import (
    build_latest_salary_entry,
    build_recent_monthly_timeline,
    compute_career_growth,
    load_entries_chronological,
)


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
        totals = compute_totals(qs)

        # 3. Company Breakdown Aggregation
        company_breakdown = compute_company_breakdown(qs, currency_code, self.format_currency)

        # 4. Dynamic Yearly Summary & YoY Growth Calculation
        yearly = compute_yearly_summary(qs, currency_code, self.format_currency)

        # 5. Chronological Entry Analysis (Earliest -> Latest)
        all_entries_asc = load_entries_chronological(qs)
        growth = compute_career_growth(all_entries_asc, totals["total_count"])

        # 6. Timeline Entry Assembly (chronological, oldest -> newest)
        recent_monthly_timeline = build_recent_monthly_timeline(
            all_entries_asc, limit, currency_code, self.format_currency
        )
        latest_salary_entry = build_latest_salary_entry(all_entries_asc, currency_code, self.format_currency)

        return {
            "currency": currency_code,
            "latest_active_year": yearly["latest_active_year"],
            "latest_active_year_summary": yearly["latest_active_year_summary"],
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
                f"(out of {totals['total_count']} total salary entries on record) when no explicit limit is given, "
                f"sorted chronologically OLDEST-FIRST (ascending) — the LAST item in this list is the "
                f"most recent, not the first. summary, yearly_summary, and company_breakdown above are "
                f"still computed over ALL entries, not just this list. For the single most recent "
                f"salary entry, use the separate 'latest_salary_entry' field instead of scanning this "
                f"list."
            ),
            "summary": {
                "total_paid_all_time": totals["total_paid"],
                "total_paid_all_time_formatted": self.format_currency(totals["total_paid"], currency_code),
                "total_expected_all_time": totals["total_expected"],
                "total_expected_all_time_formatted": self.format_currency(totals["total_expected"], currency_code),
                "total_bonus_all_time": totals["total_bonus"],
                "total_bonus_all_time_formatted": self.format_currency(totals["total_bonus"], currency_code),
                "total_entries_count": totals["total_count"],
                "average_monthly_paid": round(totals["avg_monthly_paid"], 2),
                "average_monthly_paid_formatted": self.format_currency(round(totals["avg_monthly_paid"], 2), currency_code),
                "career_overall_growth_pct": growth["career_overall_growth_pct"],
                "paid_consistency_pct": growth["paid_consistency_pct"],
                "currency": currency_code,
                "company_breakdown": company_breakdown,
            },
            "yearly_summary": yearly["yearly_summary"],
        }
