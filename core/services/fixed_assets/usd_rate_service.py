# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false

"""Single source of truth for the "USD Exchange Rate" shown on Fixed Asset
General / Renovation / Acquisition Cost / Furniture tabs.

The rate is always expressed as "how many units of the purchase currency
equal 1 USD" (e.g. ~48.5 for EGP, ~3.75 for SAR, 1.0 for USD) — so
converting to USD is always `amount / rate`, uniformly, for every
currency. This was ported from the original frontend logic in
static/js/fixed_assets/currency.js (applyPurchaseUsdRateByCurrency),
which only got this right for EGP and returned the opposite convention
("1 unit of currency is worth this many USD") for every other currency —
that inconsistency meant Acquisition Cost / Furniture / Renovation rows
(which always divide by this rate, see acquisition_costs_collect.js,
furniture_row.js, renovations_collect.js) silently produced wildly wrong
USD totals for any purchase currency other than EGP or USD. Fixed here so
every consumer of this rate can divide uniformly.
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
        from core.services.shared.currency_conversion_service import RATE_PIVOT

        currency = Currency.objects.filter(pk=currency_id).first()
        currency_code = (currency.code if currency else "").upper()

        if currency_code == "USD":
            return UsdRateResult(rate=1.0)

        latest_rates = self._latest_rate_by_code()

        usd_buy_rate = self._get_buy_rate(latest_rates, "USD")
        if not usd_buy_rate:
            raise UsdRateError("Error loading exchange rates.")

        if currency_code == RATE_PIVOT or not currency_code:
            # The exchange-rate table is always pivoted through RATE_PIVOT
            # ("EGP") and never stores a row for it (see
            # ExchangeRateService.CURRENCY_NAMES) — this is a structural
            # fact about the table, independent of any user's own base
            # currency. usd_buy_rate IS already "EGP per 1 USD", which is
            # exactly this function's target convention, so use it as-is.
            return UsdRateResult(rate=round(usd_buy_rate, 5))

        currency_buy_rate = self._get_buy_rate(latest_rates, currency_code)
        if not currency_buy_rate:
            raise UsdRateError("Error loading exchange rates.")

        # currency_buy_rate = "EGP per 1 unit of currency", usd_buy_rate =
        # "EGP per 1 USD" -> (EGP/USD) / (EGP/currency) = currency per USD.
        rate = usd_buy_rate / currency_buy_rate
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
