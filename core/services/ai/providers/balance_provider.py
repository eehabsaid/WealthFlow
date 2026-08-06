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
        balances = list(
            BalanceEntry.objects.select_related("currency", "bank")
            .values("id", "title", "amount", "currency__code", "bank__name", "balance_type")[:limit]
        )
        return {"items": balances}
