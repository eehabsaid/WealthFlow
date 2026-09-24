"""
Data-loading mixin for NetWorthService.

NOTE (200-line file convention): split out of the original monolithic
core/services/balance/net_worth_service.py (1162 lines). Holds every
`self._cached(...)`-backed DB loader plus the low-level asset/liquidity
query helpers. See sibling modules in this package: helpers.py (stateless
utils), portfolio.py (portfolio_components/balance_payload/
fixed_assets_snapshot), certificate/ (certificate_forecast_payload split
by phase), gold/ (gold trend/signal calc), assets/ (fixed-asset builders).
__init__.py assembles NetWorthService from all mixins.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from django.db.models import Sum, Q

from core.models import (
    BalanceEntry,
    BankCertificate,
    FixedAsset,
    GoldPrice,
    GoldPriceHistory,
    GoldPuritySetting,
    _is_certificate_active,
)

from core.services.balance.net_worth_service.helpers import (
    REAL_ESTATE_ASSET_TYPES,
    VEHICLE_ASSET_TYPES,
    OTHER_ASSET_TYPES,
    _normalize_gold_purity,
    _to_float,
)
from core.services.balance.net_worth_service.balance_entries import ProjectedBalanceEntriesMixin


class NetWorthDataAccessMixin(ProjectedBalanceEntriesMixin):
    """Cached DB loaders shared by portfolio and forecast computations."""

    def _base_code(self) -> str:
        from core.services.shared.base_currency import get_user_base_code
        return self._cached("base_code", lambda: get_user_base_code(self.owner))

    def _latest_rates(self) -> Dict[str, float]:
        """code -> value of one unit in the user's default currency."""
        def _load():
            from core.services.shared.base_currency import base_rates
            return base_rates(self.owner)

        return self._cached("latest_rates", _load)

    def _gold_rate(self) -> float:
        """Value of one unit of the gold-price currency in the default currency."""
        from core.services.shared.base_currency import GOLD_PRICE_CURRENCY
        return _to_float(self._latest_rates().get(GOLD_PRICE_CURRENCY, 1.0))

    def _latest_gold_price(self):
        return self._cached("latest_gold", lambda: GoldPrice.objects.order_by("-fetched_at").first())

    def _gold_cashback_by_key(self) -> Dict[str, float]:
        def _load():
            return {
                str(setting.key or "").lower(): _to_float(setting.cashback_per_gram)
                for setting in GoldPuritySetting.objects.filter(is_active=True, owner=self.owner)
            }

        return self._cached("gold_cashback", _load)

    def _sell_price_per_gram(self, purity_key: str) -> float:
        latest_gold = self._latest_gold_price()
        if not latest_gold:
            return 0.0

        if purity_key == "22k":
            return _to_float(latest_gold.carat_22k)
        if purity_key == "21k":
            return _to_float(latest_gold.carat_21k)
        if purity_key == "18k":
            return _to_float(latest_gold.carat_18k)
        return _to_float(latest_gold.carat_24k)

    def gold_unit_value(self, purity) -> dict:
        """Per-gram value of a gold balance entry, same formula as portfolio_components():
        (sell price for the purity + configured cashback per gram) * gold-price-currency rate."""
        key = _normalize_gold_purity(purity)
        sell = self._sell_price_per_gram(key)
        cashback = _to_float(self._gold_cashback_by_key().get(key, 0.0))
        return {
            "purity": key, "sell_price_per_gram": sell, "cashback_per_gram": cashback,
            "value_per_gram": (sell + cashback) * self._gold_rate(),
        }

    def _active_certificates(self) -> List[BankCertificate]:
        def _load():
            certs = BankCertificate.objects.select_related("bank", "currency").filter(owner=self.owner)
            return [c for c in certs if _is_certificate_active(c)]

        return self._cached("active_certs", _load)

    def _certificate_projection_map(self) -> Dict[Tuple[int, int], float]:
        def _load():
            grouped: Dict[Tuple[int, int], float] = {}
            for cert in self._active_certificates():
                key = (cert.bank_id or 0, cert.currency_id or 0)
                grouped[key] = grouped.get(key, 0.0) + _to_float(cert.amount)
            return grouped

        return self._cached("cert_projection", _load)

    def _converted_egp(self, amount: float, currency_code: str, rates: Dict[str, float]) -> float:
        from core.services.balance.net_worth_calculations import converted_egp
        return converted_egp(amount, currency_code, rates)

    def _fixed_assets_breakdown(self) -> Dict[str, float]:
        def _load():
            owned = FixedAsset.objects.filter(owner=self.owner, status="Owned")
            agg = owned.aggregate(
                real_estate=Sum("current_market_value", filter=Q(asset_type__in=REAL_ESTATE_ASSET_TYPES)),
                vehicles=Sum("current_market_value", filter=Q(asset_type__in=VEHICLE_ASSET_TYPES)),
                other_assets=Sum("current_market_value", filter=Q(asset_type__in=OTHER_ASSET_TYPES)),
            )
            return {
                "real_estate": _to_float(agg.get("real_estate")),
                "vehicles": _to_float(agg.get("vehicles")),
                "other_assets": _to_float(agg.get("other_assets")),
            }

        return self._cached("fixed_assets_breakdown", _load)

    def _strict_liquid_assets_egp(self) -> float:
        """
        Liquidity definition for recommendation calibration:
        - Source: BalanceEntry only
        - Filter: balance_type = Cash and currency != Gold (case-insensitive)
        - Conversion: latest BUY rate into the user's default currency
        """
        rates = self._latest_rates()
        total = 0.0

        rows = (
            BalanceEntry.objects.select_related("currency")
            .filter(owner=self.owner, balance_type__iexact=BalanceEntry.BalanceType.CASH)
            .exclude(currency__code__iexact="GOLD")
        )

        for row in rows:
            code = str(getattr(row.currency, "code", "") or "").upper()
            amount = _to_float(row.amount)
            if code:
                total += amount * _to_float(rates.get(code))

        return total

    def _strict_egp_cash_balance(self) -> float:
        """
        Strict default-currency cash for Financial Intelligence card:
        - Source: BalanceEntry only
        - Filter: balance_type = cash AND currency = the user's default (case-insensitive)
        - Includes both bank and non-bank rows
        """
        agg = (
            BalanceEntry.objects.filter(
                owner=self.owner,
                balance_type__iexact=BalanceEntry.BalanceType.CASH,
                currency__code__iexact=self._base_code(),
            ).aggregate(total=Sum("amount"))
        )
        return _to_float(agg.get("total"))

    def _gold_trend_change(self, history: List[GoldPriceHistory], window_days: int) -> float:
        from core.services.balance.net_worth_calculations import gold_trend_change
        return gold_trend_change(history, window_days)

    def _append_unique(self, items: List[str], value: str) -> None:
        from core.services.balance.net_worth_calculations import append_unique
        append_unique(items, value)
