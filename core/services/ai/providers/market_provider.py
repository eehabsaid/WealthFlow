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

    def get_query_capabilities(self) -> list[Any]:
        from core.services.ai.query_engine.executors.market import CAPABILITIES

        return list(CAPABILITIES)

    def get_data(self, user: Any, limit: int | None = None) -> dict[str, Any]:
        latest_rate_ids = ExchangeRate.objects.values("currency_code").annotate(max_id=Max("id")).values_list("max_id", flat=True)
        qs = ExchangeRate.objects.filter(id__in=latest_rate_ids).values("currency_code", "mid_rate", "buy_rate", "sell_rate", "fetched_at")
        from core.services.shared.market_profile import is_gulf_user, spot_gold_snapshot

        gulf = user is not None and getattr(user, "is_authenticated", False) and is_gulf_user(user)
        if gulf:
            qs = qs.exclude(currency_code__iexact="EGP")  # Gulf-market users have no EGP anywhere
        if limit is not None and limit > 0:
            qs = qs[:limit]
        rates = list(qs)
        gold = GoldPrice.objects.order_by("-fetched_at", "-id").first()
        gold_data = gold.to_dict() if gold else None
        if gold_data is not None and gulf:
            gold_data.update(spot_gold_snapshot(user, gold))  # spot price in the user's own currency
        return {
            "exchange_rates": rates,
            "latest_gold_price": gold_data,
        }
