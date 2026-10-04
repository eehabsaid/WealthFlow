"""Gold history as the viewer's market sees it (Financial Advisor > Performance).

Stored gold history is quoted in GOLD_PRICE_CURRENCY (Egyptian dealer prices).
Gulf-market users (SAR/AED base, no EGP) get international-spot prices in
their own base currency instead, mirroring market_profile.spot_gold_snapshot,
so the Performance tab never shows an EGP figure to them.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from core.services.shared.base_currency import GOLD_PRICE_CURRENCY, get_user_base_code
from core.services.shared.market_profile import CARAT_PURITY, is_gulf_user


class GoldMarketView:
    """Converts stored GoldPriceHistory rows to the viewer's gold currency."""

    def __init__(self, owner):
        from core.services.shared.currency_conversion_service import CurrencyConversionService

        self.gulf = bool(owner is not None and is_gulf_user(owner))
        self.currency = get_user_base_code(owner) if self.gulf else GOLD_PRICE_CURRENCY
        self._usd_rate: Optional[Decimal] = None
        self._egp_rate: Optional[Decimal] = None
        if self.gulf:
            self._usd_rate = CurrencyConversionService.calculate_exchange_rate("USD", self.currency)
            self._egp_rate = CurrencyConversionService.calculate_exchange_rate(
                GOLD_PRICE_CURRENCY, self.currency
            )

    def price(self, row, karat: str) -> float:
        """Price per gram of `karat` ('24k'/'21k'/'18k') in self.currency."""
        stored = float(getattr(row, f"carat_{karat}") or 0)
        if not self.gulf:
            return stored
        usd_gram = Decimal(str(getattr(row, "usd_gram_24k", 0) or 0))
        if usd_gram > 0 and self._usd_rate:
            return float(usd_gram * CARAT_PURITY[karat] * self._usd_rate)
        return float(Decimal(str(stored)) * (self._egp_rate or Decimal(0)))  # legacy row without spot

    def factor_21k(self, latest_row) -> float:
        """Multiplier turning stored (EGP) 21K figures into self.currency."""
        if not self.gulf or latest_row is None:
            return 1.0
        stored = float(latest_row.carat_21k or 0)
        return self.price(latest_row, "21k") / stored if stored > 0 else float(self._egp_rate or 1)


def gold_market_payload(view: GoldMarketView) -> Dict[str, Any]:
    return {"currency": view.currency, "market": "spot" if view.gulf else "dealer"}
