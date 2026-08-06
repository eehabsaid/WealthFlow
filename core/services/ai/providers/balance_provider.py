"""
Balance Data Provider for AI business context. Read-only.
"""

from __future__ import annotations

from typing import Any
from core.models import BalanceEntry
from core.services.ai.providers.base import BaseContextProvider


class BalanceDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "balances"

    @property
    def name(self) -> str:
        return "Bank & Cash Balances"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Cash & Bank Balance Tracking",
            "provided_by": "BalanceDataProvider",
            "consumes": ["BalanceEntry", "Bank", "Currency"],
            "used_by": ["Dashboard", "Portfolio", "NetWorthService"],
            "inputs": ["currency_id", "bank_id"],
            "outputs": ["title", "amount", "currency_code", "bank_name", "balance_type"],
            "description": "Provides real-time liquid account and bank balance snapshots.",
        }]

    def get_data(self, user: Any, limit: int = 20) -> dict[str, Any]:
        from django.db.models import Sum
        by_curr = list(
            BalanceEntry.objects.values("currency__code")
            .annotate(total_amount=Sum("amount"))
            .order_by("-total_amount")
        )
        tot_egp = sum(
            float(b.amount or 0) for b in BalanceEntry.objects.filter(currency__code__iexact="EGP")
        )
        balances = list(
            BalanceEntry.objects.select_related("currency", "bank")
            .values("id", "title", "amount", "currency__code", "bank__name", "balance_type")[:limit]
        )
        return {
            "summary": {
                "total_liquid_egp": tot_egp,
                "balances_by_currency": by_curr,
                "total_accounts_count": BalanceEntry.objects.count(),
            },
            "items": balances,
        }
