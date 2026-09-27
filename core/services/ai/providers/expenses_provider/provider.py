"""
Expenses Data Provider for AI business context. Read-only.
Enforces multi-tenant scoping, category breakdown calculations, spending totals, and home currency conversions.
"""

from __future__ import annotations

from typing import Any
from core.models import Expense
from core.services.ai.providers.base import BaseContextProvider
from core.services.ai.providers.expenses_provider.aggregation import (
    build_category_breakdown,
    build_monthly_category_breakdown,
    build_monthly_summary,
)

# Caps how many individual transactions are included in the AI-facing 'recent_expenses'
# list, independent of the caller's `limit` param. Aggregates (summary, category_breakdown)
# are always computed over the FULL queryset regardless of this cap — only the per-row
# list is capped, to keep the JSON payload small enough to reliably fit in the model's
# context window without truncation.
MAX_RECENT_EXPENSES_FOR_AI = 20

# Caps how many (year, month) entries are included in the AI-facing
# 'monthly_summary' list. monthly_summary lives in the HIGH-priority summary
# block (never trimmed by the token-budget degrader — see split_payload_blocks
# / _LARGE_SUMMARY_KEYS in context_builder_service/formatting.py), so on an
# account with many months of history this array alone could consume most of
# the data budget and squeeze the LOW-priority recent_expenses block out.
# Capped the same way recent_expenses already is, for the same reason.
MAX_MONTHLY_SUMMARY_MONTHS_FOR_AI = 240

# monthly_category_breakdown carries a category split PER month, so it grows
# much faster than monthly_summary (months x categories, not just months).
# Capped tighter — recent months are what "detail/breakdown for <month>"
# questions are almost always about; older months still have their (total-
# only) figure available via monthly_summary.
MAX_MONTHLY_CATEGORY_BREAKDOWN_MONTHS_FOR_AI = 6


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
            "outputs": ["summary", "category_breakdown", "monthly_category_breakdown", "recent_expenses"],
            "description": "Calculates total spending, all-time and per-month category breakdowns, top spending categories, and pre-converted primary currency metrics deterministically.",
        }]

    def get_data(self, user: Any, limit: int | None = None) -> dict[str, Any]:
        home_currency = self.get_user_primary_currency(user)
        fmt = lambda v: self.format_currency(v, home_currency)  # noqa: E731

        qs = Expense.objects.all()
        if user and user.is_authenticated:
            qs = qs.filter(owner=user)
        qs = qs.select_related("category", "currency").order_by("-date")
        if limit is not None and limit > 0:
            qs = qs[:limit]
        expenses_raw = list(qs)

        total_spending_home = 0.0
        by_category: dict[str, float] = {}
        by_month: dict[tuple[int, int], dict[str, float]] = {}
        by_month_category: dict[tuple[int, int], dict[str, float]] = {}
        recent_expenses = []

        for exp in expenses_raw:
            c_code = exp.currency.code if exp.currency else home_currency
            amt = float(exp.amount or 0)
            # amount_base is pre-calculated at save time in the user's default
            # currency (amount * exchange_rate), which is also the AI's home currency.
            amt_home = float(exp.amount_base or 0)
            cat_name = exp.category.name if exp.category else "Uncategorized"

            total_spending_home += amt_home
            by_category[cat_name] = by_category.get(cat_name, 0.0) + amt_home

            month_key = (exp.year, exp.month)
            month_bucket = by_month.setdefault(month_key, {"total": 0.0, "count": 0.0})
            month_bucket["total"] += amt_home
            month_bucket["count"] += 1
            month_cat_bucket = by_month_category.setdefault(month_key, {})
            month_cat_bucket[cat_name] = month_cat_bucket.get(cat_name, 0.0) + amt_home

            recent_expenses.append({
                "id": exp.id,
                "category": cat_name,
                "amount": amt,
                "currency": c_code,
                "amount_formatted": self.format_currency(amt, c_code),
                "amount_in_home_currency": amt_home,
                "amount_in_home_currency_formatted": fmt(amt_home),
                "date": exp.date.isoformat() if exp.date else "",
                "notes": exp.notes or "",
            })

        category_breakdown = build_category_breakdown(by_category, total_spending_home, fmt)
        top_category_name = next(iter(category_breakdown), None)
        top_category_amount = category_breakdown[top_category_name]["total_spending"] if top_category_name else 0.0

        monthly_summary = build_monthly_summary(by_month, fmt)
        monthly_category_breakdown = build_monthly_category_breakdown(
            by_month_category, by_month, MAX_MONTHLY_CATEGORY_BREAKDOWN_MONTHS_FOR_AI, fmt
        )

        # latest_month_summary and last_expense are derived from the FULL
        # (uncapped) monthly_summary / recent_expenses lists computed above,
        # before either is capped for the AI payload below — so they're
        # always correct even when the capped lists get degraded/dropped
        # under token budget pressure.
        latest_month_summary = monthly_summary[0] if monthly_summary else None
        last_expense = recent_expenses[0] if recent_expenses else None

        return {
            "summary": {
                "total_spending_in_home_currency": round(total_spending_home, 2),
                "total_spending_in_home_currency_formatted": fmt(round(total_spending_home, 2)),
                "top_category": top_category_name or "N/A",
                "top_category_spending_formatted": fmt(round(top_category_amount, 2)),
                "total_transactions_count": len(recent_expenses),
                "home_currency": home_currency,
                # Single most-recent transaction, promoted into the HIGH-priority
                # (never-trimmed) summary block so "what's my last/most recent
                # expense" is answered correctly even under budget pressure.
                "last_expense": last_expense,
            },
            "last_expense_note": (
                "summary.last_expense is the single most recent individual expense "
                "transaction (by date). For 'what is my last/most recent expense' "
                "questions, use this field directly — do not use monthly_summary or "
                "the all-time summary total, which are aggregates, not a single transaction."
            ),
            "summary_note": (
                "summary.total_spending_in_home_currency is an ALL-TIME total across every expense "
                "on record. For any request scoped to a specific month or year (e.g. 'this month', "
                "'September 2026'), do NOT use this field — use monthly_summary (for a total) or "
                "monthly_category_breakdown (for a per-category detail/table) instead."
            ),
            "category_breakdown": category_breakdown,
            "category_breakdown_note": (
                "category_breakdown is an ALL-TIME per-category total across every expense on record "
                "— it is NOT scoped to any particular month or year. For a request about a specific "
                "month (e.g. 'detail the expenses for September 2026', 'breakdown by category for "
                "last month'), do NOT use this field — use monthly_category_breakdown instead, which "
                "has the same category-total shape but scoped to one (year, month) at a time."
            ),
            "monthly_summary": monthly_summary[:MAX_MONTHLY_SUMMARY_MONTHS_FOR_AI],
            "latest_month_summary": latest_month_summary,
            "monthly_summary_note": (
                "monthly_summary is the authoritative, pre-aggregated TOTAL (no category split) per "
                "(year, month), newest-first, computed over ALL transactions (not just recent_expenses), "
                f"capped here to the most recent {MAX_MONTHLY_SUMMARY_MONTHS_FOR_AI} months out of "
                f"{len(monthly_summary)} total on record. For a plain 'total expenses for <month/year>' "
                "question, find the entry matching that year+month and quote its total_spending_formatted "
                "exactly — do not sum recent_expenses or use the all-time summary total. For a per-category "
                "breakdown of a month, use monthly_category_breakdown instead. latest_month_summary is the "
                "same object as index 0 of this list and is always present even if the requested month "
                "falls outside the cap."
            ),
            "monthly_category_breakdown": monthly_category_breakdown,
            "monthly_category_breakdown_note": (
                "monthly_category_breakdown is the authoritative, pre-aggregated per-CATEGORY total for "
                "one (year, month) at a time, newest-first, computed over ALL transactions — this is the "
                "field to use for 'detail/breakdown/table of expenses for <month>' questions. Find the "
                "entry matching the requested year+month and quote its categories.<name>.total_spending_formatted "
                "values and its own total_spending_formatted exactly. Do NOT compute this yourself by "
                "filtering recent_expenses (it's a capped, possibly-incomplete subset) and do NOT use "
                f"category_breakdown (all-time, not month-scoped). Capped to the most recent "
                f"{MAX_MONTHLY_CATEGORY_BREAKDOWN_MONTHS_FOR_AI} months — if the requested month isn't "
                "here and monthly_summary shows it has transactions, say the per-category detail isn't "
                "available for that month but the total is <total from monthly_summary>."
            ),
            "recent_expenses": recent_expenses[:MAX_RECENT_EXPENSES_FOR_AI],
            "recent_expenses_note": (
                f"recent_expenses is a flat list of individual transactions ordered newest-first "
                f"by date (index 0 = the single latest expense entry). It is capped to the {MAX_RECENT_EXPENSES_FOR_AI} "
                f"most recent transactions out of {len(recent_expenses)} total on record — summary, "
                f"category_breakdown, monthly_summary, and monthly_category_breakdown above are all "
                f"computed over ALL transactions, not just this list. Do not use this list to compute "
                f"a month or category total yourself — use the fields above instead."
            ),
        }
