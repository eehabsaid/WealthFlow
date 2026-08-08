"""
Expenses Data Provider for AI business context. Read-only.
Enforces multi-tenant scoping, category breakdown calculations, spending totals, and home currency conversions.
"""

from __future__ import annotations

from typing import Any
from core.models import Expense
from core.services.ai.providers.base import BaseContextProvider


class ExpensesDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "expenses"

    @property
    def name(self) -> str:
        return "Spending & Expense Analytics"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Spending & Expense Analytics",
            "provided_by": "ExpensesDataProvider",
            "consumes": ["Expense", "ExpenseCategory", "Currency"],
            "used_by": ["Financial Advisor", "Spending Intelligence", "AI Advisor"],
            "inputs": ["user"],
            "outputs": ["summary", "category_breakdown", "recent_expenses"],
            "description": "Calculates total spending, category expense breakdown %, top spending categories, and pre-converted primary currency metrics deterministically.",
        }]

    def get_data(self, user: Any, limit: int | None = None) -> dict[str, Any]:
        home_currency = self.get_user_primary_currency(user)

        # 1. Multi-tenant User Scoping
        qs = Expense.objects.all()
        has_user_field = any(f.name == "user" for f in Expense._meta.fields)
        if user and user.is_authenticated and has_user_field:
            qs = qs.filter(user=user)

        qs = qs.select_related("category", "currency").order_by("-date")
        if limit is not None and limit > 0:
            qs = qs[:limit]

        expenses_raw = list(qs)

        total_spending_home = 0.0
        by_category: dict[str, float] = {}
        recent_expenses = []

        for exp in expenses_raw:
            c_code = exp.currency.code if exp.currency else home_currency
            amt = float(exp.amount or 0)
            amt_home = self.convert_to_home_currency(amt, c_code, home_currency)

            cat_name = exp.category.name if exp.category else "Uncategorized"

            total_spending_home += amt_home
            by_category[cat_name] = by_category.get(cat_name, 0.0) + amt_home

            recent_expenses.append({
                "id": exp.id,
                "category": cat_name,
                "amount": amt,
                "currency": c_code,
                "amount_formatted": self.format_currency(amt, c_code),
                "amount_in_home_currency": amt_home,
                "amount_in_home_currency_formatted": self.format_currency(amt_home, home_currency),
                "date": exp.date.isoformat() if exp.date else "",
                "notes": exp.notes or "",
            })

        # Category Breakdown with Percentages
        category_breakdown = {}
        top_category_name = None
        top_category_amount = 0.0

        for cat_name, cat_val in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
            pct = (round((cat_val / total_spending_home) * 100.0, 1)) if total_spending_home > 0 else 0.0
            if cat_val > top_category_amount:
                top_category_amount = cat_val
                top_category_name = cat_name

            category_breakdown[cat_name] = {
                "total_spending": round(cat_val, 2),
                "total_spending_formatted": self.format_currency(round(cat_val, 2), home_currency),
                "percentage": pct,
                "percentage_formatted": f"{pct:.1f}%",
            }

        return {
            "summary": {
                "total_spending_in_home_currency": round(total_spending_home, 2),
                "total_spending_in_home_currency_formatted": self.format_currency(round(total_spending_home, 2), home_currency),
                "top_category": top_category_name or "N/A",
                "top_category_spending_formatted": self.format_currency(round(top_category_amount, 2), home_currency),
                "total_transactions_count": len(recent_expenses),
                "home_currency": home_currency,
            },
            "category_breakdown": category_breakdown,
            "recent_expenses": recent_expenses,
        }
