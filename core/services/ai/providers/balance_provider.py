"""
Balance Data Provider for AI business context. Read-only.
Enforces multi-tenant scoping, deterministic ORM aggregation, and home currency conversions.
"""

from __future__ import annotations

from typing import Any
from core.models import BalanceEntry
from core.services.ai.providers.base import BaseContextProvider

# Caps how many accounts are included in the AI-facing 'items' list when the caller
# does not pass an explicit `limit`. Aggregates (summary) are always computed over
# ALL accounts regardless of this cap — only the per-row list is capped, to keep the
# JSON payload small enough to reliably fit in the model's context window without
# truncation.
MAX_BALANCE_ITEMS_FOR_AI = 20

class BalanceDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "balance"

    @property
    def name(self) -> str:
        return "Bank & Liquid Balances"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Bank & Liquid Balances",
            "provided_by": "BalanceDataProvider",
            "consumes": ["BalanceEntry", "Bank", "Currency"],
            "used_by": ["Financial Advisor", "Cash Flow Forecast", "AI Advisor"],
            "inputs": ["user"],
            "outputs": ["summary", "items", "balances_by_currency"],
            "description": "Calculates liquid cash & bank balances, pre-converted total liquid net worth in primary currency, and currency breakdowns deterministically.",
        }]

    def get_data(self, user: Any, limit: int | None = None) -> dict[str, Any]:
        home_currency = self.get_user_primary_currency(user)

        # 1. Multi-tenant User Scoping
        qs = BalanceEntry.objects.all()
        has_user_field = any(f.name == "user" for f in BalanceEntry._meta.fields)
        if user and user.is_authenticated and has_user_field:
            qs = qs.filter(user=user)

        qs = qs.select_related("bank", "currency").order_by("-id")

        items_raw = list(qs)

        total_liquid_home = 0.0
        balances_by_curr: dict[str, float] = {}
        items = []

        for entry in items_raw:
            c_code = entry.currency.code if entry.currency else home_currency
            amt = float(entry.amount or 0)
            amt_home = self.convert_to_home_currency(amt, c_code, home_currency)

            total_liquid_home += amt_home
            balances_by_curr[c_code] = balances_by_curr.get(c_code, 0.0) + amt

            items.append({
                "id": entry.id,
                "title": entry.title,
                "balance_type": entry.balance_type,
                "bank_name": entry.bank.name if entry.bank else "",
                "amount": amt,
                "currency": c_code,
                "amount_formatted": self.format_currency(amt, c_code),
                "amount_in_home_currency": amt_home,
                "amount_in_home_currency_formatted": self.format_currency(amt_home, home_currency),
                "notes": entry.notes or "",
            })

        by_curr_formatted = {
            code: self.format_currency(val, code)
            for code, val in balances_by_curr.items()
        }

        effective_limit = limit if (limit is not None and limit > 0) else MAX_BALANCE_ITEMS_FOR_AI

        return {
            "summary": {
                "total_liquid_in_home_currency": round(total_liquid_home, 2),
                "total_liquid_in_home_currency_formatted": self.format_currency(round(total_liquid_home, 2), home_currency),
                "home_currency": home_currency,
                "total_accounts_count": len(items),
                "balances_by_currency": by_curr_formatted,
            },
            "items": items[:effective_limit],
            "items_note": (
                f"items is capped to {effective_limit} accounts out of {len(items)} total on record — "
                f"summary above is still computed over ALL accounts, not just this list."
            ),
        }
