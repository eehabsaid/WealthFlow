"""Budgets & recurring transactions for AI business context. Read-only.

Spend is read through BudgetService.compute_spent (Expense.amount_base, already in the owner's
base currency), so a budget set in any currency is compared correctly. Owner-scoped like every provider.
"""

from __future__ import annotations

from typing import Any

from core.services.ai.providers.base import BaseContextProvider


class BudgetsDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "budgets"

    @property
    def name(self) -> str:
        return "Budgets & Recurring Transactions"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Budget Status & Recurring Commitments",
            "provided_by": "BudgetsDataProvider",
            "consumes": ["Budget", "RecurringTransaction", "Expense"],
            "used_by": ["AI Chat"],
            "inputs": ["owner"],
            "outputs": ["budgets", "recurring_transactions"],
            "description": "Per-budget limit, spend this period and % used; active recurring bills with next due date.",
        }]

    def get_query_capabilities(self) -> list[Any]:
        from core.services.ai.query_engine.executors.budgets import CAPABILITIES

        return list(CAPABILITIES)

    def get_data(self, user: Any, limit: int | None = None) -> dict[str, Any]:
        from core.models import RecurringTransaction
        from core.services.budgets.budget_service import BudgetService

        if user is None or not getattr(user, "is_authenticated", False):
            return {"budgets": [], "recurring_transactions": [], "currency": ""}
        budgets = BudgetService.list_with_spend(user)
        recurring = [
            r.to_dict()
            for r in RecurringTransaction.objects.filter(owner=user).select_related("category", "currency")
        ]
        if limit is not None and limit > 0:
            budgets, recurring = budgets[:limit], recurring[:limit]
        return {"budgets": budgets, "recurring_transactions": recurring, "currency": self.get_user_primary_currency(user)}
