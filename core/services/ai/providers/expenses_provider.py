"""
Expenses Data Provider for AI business context. Read-only.
Enforces multi-tenant scoping, category breakdown calculations, spending totals, and home currency conversions.
"""

from __future__ import annotations

from typing import Any
from core.models import Expense
from core.services.ai.providers.base import BaseContextProvider

# Caps how many individual transactions are included in the AI-facing 'recent_expenses'
# list, independent of the caller's `limit` param. Aggregates (summary, category_breakdown)
# are always computed over the FULL queryset regardless of this cap — only the per-row
# list is capped, to keep the JSON payload small enough to reliably fit in the model's
# context window without truncation.
MAX_RECENT_EXPENSES_FOR_AI = 20

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
        by_month: dict[tuple[int, int], dict[str, float]] = {}
        recent_expenses = []

        for exp in expenses_raw:
            c_code = exp.currency.code if exp.currency else home_currency
            amt = float(exp.amount or 0)
            # amount_egp is pre-calculated at save time (amount * exchange_rate -> EGP).
            amt_egp = float(exp.amount_egp or 0)
            amt_home = amt_egp if home_currency == "EGP" else self.convert_to_home_currency(amt_egp, "EGP", home_currency)

            cat_name = exp.category.name if exp.category else "Uncategorized"

            total_spending_home += amt_home
            by_category[cat_name] = by_category.get(cat_name, 0.0) + amt_home

            month_key = (exp.year, exp.month)
            month_bucket = by_month.setdefault(month_key, {"total": 0.0, "count": 0.0})
            month_bucket["total"] += amt_home
            month_bucket["count"] += 1

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

        # Monthly Summary — deterministic per (year, month) totals, newest-first.
        monthly_summary = []
        for (m_year, m_month) in sorted(by_month.keys(), reverse=True):
            bucket = by_month[(m_year, m_month)]
            monthly_summary.append({
                "year": m_year,
                "month": m_month,
                "total_spending": round(bucket["total"], 2),
                "total_spending_formatted": self.format_currency(round(bucket["total"], 2), home_currency),
                "transactions_count": int(bucket["count"]),
                "currency": home_currency,
            })
        latest_month_summary = monthly_summary[0] if monthly_summary else None

        return {
            "summary": {
                "total_spending_in_home_currency": round(total_spending_home, 2),
                "total_spending_in_home_currency_formatted": self.format_currency(round(total_spending_home, 2), home_currency),
                "top_category": top_category_name or "N/A",
                "top_category_spending_formatted": self.format_currency(round(top_category_amount, 2), home_currency),
                "total_transactions_count": len(recent_expenses),
                "home_currency": home_currency,
            },
            "summary_note": (
                "summary.total_spending_in_home_currency is an ALL-TIME total across every expense "
                "on record. For any request scoped to a specific month or year (e.g. 'this month', "
                "'September 2026'), do NOT use this field — use monthly_summary instead."
            ),
            "category_breakdown": category_breakdown,
            "monthly_summary": monthly_summary,
            "latest_month_summary": latest_month_summary,
            "monthly_summary_note": (
                "monthly_summary is the authoritative, pre-aggregated list of total spending per "
                "(year, month), newest-first, computed over ALL transactions (not just recent_expenses). "
                "For any 'total expenses for <month/year>' question, find the entry matching that "
                "year+month and quote its total_spending_formatted exactly — do not sum recent_expenses "
                "or use the all-time summary total. latest_month_summary is the same object as index 0 "
                "of this list. If no entry matches the requested year+month, there are zero expenses "
                "for that period."
            ),
            "recent_expenses": recent_expenses[:MAX_RECENT_EXPENSES_FOR_AI],
            "recent_expenses_note": (
                f"recent_expenses is a flat list of individual transactions ordered newest-first "
                f"by date (index 0 = the single latest expense entry). It is capped to the {MAX_RECENT_EXPENSES_FOR_AI} "
                f"most recent transactions out of {len(recent_expenses)} total on record — summary, "
                f"category_breakdown, and monthly_summary above are still computed over ALL transactions, "
                f"not just this list. For month/year totals, use monthly_summary, not this list."
            ),
        }
