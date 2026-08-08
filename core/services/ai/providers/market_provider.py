"""
Market Data Provider (Exchange Rates & Gold Prices) for AI business context. Read-only.
"""

from __future__ import annotations

from typing import Any
from django.db.models import Max
from core.models import ExchangeRate, GoldPrice
from core.services.ai.providers.base import BaseContextProvider


class MarketDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "market_data"

    @property
    def name(self) -> str:
        return "Exchange Rates & Gold Prices"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Live Foreign Exchange & Gold Price Tracking",
            "provided_by": "MarketDataProvider",
            "consumes": ["ExchangeRate", "GoldPrice"],
            "used_by": ["Performance", "NetWorthService", "Portfolio"],
            "inputs": ["currency_code"],
            "outputs": ["exchange_rates", "latest_gold_price"],
            "description": "Fetches current forex mid/buy/sell rates and latest 24K gold market price per gram.",
        }]

    def get_data(self, user: Any, limit: int | None = None) -> dict[str, Any]:
        latest_rate_ids = ExchangeRate.objects.values("currency_code").annotate(max_id=Max("id")).values_list("max_id", flat=True)
        qs = ExchangeRate.objects.filter(id__in=latest_rate_ids).values("currency_code", "mid_rate", "buy_rate", "sell_rate", "fetched_at")
        if limit is not None and limit > 0:
            qs = qs[:limit]
        rates = list(qs)
        gold = GoldPrice.objects.order_by("-fetched_at").first()
        return {
            "exchange_rates": rates,
            "latest_gold_price": gold.to_dict() if gold else None,
        }
