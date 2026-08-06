"""
Salary Data Provider for AI business context. Read-only.
"""

from __future__ import annotations

from typing import Any
from django.db.models import Sum, Count
from core.models import SalaryEntry
from core.services.ai.providers.base import BaseContextProvider


class SalaryDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "salary"

    @property
    def name(self) -> str:
        return "Salary & Income"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Salary & Income Analytics",
            "provided_by": "SalaryDataProvider",
            "consumes": ["SalaryEntry", "Company"],
            "used_by": ["Financial Advisor", "Cash Flow Forecast", "AI Advisor"],
            "inputs": ["year", "month", "company_id"],
            "outputs": ["total_paid", "total_bonus", "total_expected", "recent_entries"],
            "description": "Calculates historical, expected, and bonus salary income per company.",
        }]

    def get_data(self, user: Any, limit: int = 20) -> dict[str, Any]:
        sal_agg = SalaryEntry.objects.aggregate(
            total_paid=Sum("paid"),
            total_bonus=Sum("bonus"),
            total_expected=Sum("expected"),
            count=Count("id"),
        )
        company_summary = list(
            SalaryEntry.objects.values("company__name")
            .annotate(total_paid=Sum("paid"), total_expected=Sum("expected"))
            .order_by("-total_paid")
        )
        recent_salaries = list(
            SalaryEntry.objects.select_related("company")
            .order_by("-year", "-month")[:min(limit, 5)]
            .values("year", "month", "company__name", "paid", "bonus", "expected")
        )
        return {
            "summary": {
                "total_paid": float(sal_agg["total_paid"] or 0),
                "total_bonus": float(sal_agg["total_bonus"] or 0),
                "total_expected": float(sal_agg["total_expected"] or 0),
                "count": sal_agg["count"] or 0,
                "company_breakdown": company_summary,
            },
            "recent_entries": recent_salaries,
        }
