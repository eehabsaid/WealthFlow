# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false

"""Single source of truth for the "USD Exchange Rate" shown on Fixed Asset
General / Renovation / Acquisition Cost / Furniture tabs.

This is a straight port of the existing frontend logic that used to live in
static/js/fixed_assets/currency.js (applyPurchaseUsdRateByCurrency). The
formula itself is UNCHANGED - only its location moved, so every "Now"
button across all Fixed Asset tabs now calls this one function instead of
each tab re-implementing the same math in JS.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.models import Currency, ExchangeRate


class UsdRateError(Exception):
    pass


@dataclass
class UsdRateResult:
    rate: float

    def to_dict(self):
        return {"rate": self.rate}


class UsdRateService:
    def get_rate_for_currency(self, currency_id) -> UsdRateResult:
        currency = Currency.objects.filter(pk=currency_id).first()
        currency_code = (currency.code if currency else "").upper()

        if currency_code == "USD":
            return UsdRateResult(rate=1.0)

        latest_rates = self._latest_rate_by_code()

        usd_buy_rate = self._get_buy_rate(latest_rates, "USD")
        if not usd_buy_rate:
            raise UsdRateError("Error loading exchange rates.")

        if currency_code == "EGP" or not currency_code:
            # Base currency is not stored in exchange-rate table; use
            # implicit buy_rate = 1.00 (same comment as the original JS).
            rate = usd_buy_rate
            return UsdRateResult(rate=round(rate, 5))

        currency_buy_rate = self._get_buy_rate(latest_rates, currency_code)
        if not currency_buy_rate:
            raise UsdRateError("Error loading exchange rates.")

        rate = currency_buy_rate / usd_buy_rate
        return UsdRateResult(rate=round(rate, 5))

    def _latest_rate_by_code(self):
        from django.db.models import Max

        latest_ids = (
            ExchangeRate.objects.values("currency_code")
            .annotate(max_id=Max("id"))
            .values_list("max_id", flat=True)
        )
        rows = ExchangeRate.objects.filter(id__in=latest_ids)
        return {row.currency_code.upper(): row for row in rows}

    def _get_buy_rate(self, rates_by_code, code):
        row = rates_by_code.get(code.upper())
        return float(row.buy_rate) if row else 0.0
