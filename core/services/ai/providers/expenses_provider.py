"""
Expenses Data Provider for AI business context. Read-only.
"""

from __future__ import annotations

from typing import Any
from django.db.models import Sum, Count
from core.models import Expense
from core.services.ai.providers.base import BaseContextProvider


class ExpensesDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "expenses"

    @property
    def name(self) -> str:
        return "Expenses & Categories"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Expense & Category Aggregation",
            "provided_by": "ExpensesDataProvider",
            "consumes": ["Expense", "ExpenseCategory"],
            "used_by": ["Spending Intelligence", "Cash Flow Forecast", "AI Advisor"],
            "inputs": ["category_id", "date_range"],
            "outputs": ["by_category", "recent_expenses"],
            "description": "Aggregates total spending per category and tracks recent expense records.",
        }]

    def get_data(self, user: Any, limit: int = 20) -> dict[str, Any]:
        exp_by_cat = list(
            Expense.objects.values("category__name")
            .annotate(total_amount=Sum("amount"), count=Count("id"))
            .order_by("-total_amount")[:limit]
        )
        recent_expenses = list(
            Expense.objects.select_related("category")
            .order_by("-date")[:limit]
            .values("date", "category__name", "amount", "description")
        )
        return {
            "by_category": exp_by_cat,
            "recent_expenses": recent_expenses,
        }
