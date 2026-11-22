# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false
"""Gold asset pricing refresh."""

from __future__ import annotations

from decimal import Decimal
from django.utils import timezone
from core.constants import GOLD_ASSET_TYPES
from core.services.fixed_assets.gold_sync_service.helpers import (
    _to_decimal,
    _gold_unit_factor,
    _gold_weight_in_grams,
    _normalize_gold_purity,
    _gold_sell_price_per_gram,
    _gold_cashback_per_gram,
    _latest_gold_price,
)


def _refresh_gold_asset_pricing(asset, gold_details=None, latest_gold_price=None):
    if asset.asset_type not in GOLD_ASSET_TYPES:
        return

    details = gold_details
    if details is None:
        details = getattr(asset, "gold_details", None)
    if details is None:
        return

    latest_gold = latest_gold_price or _latest_gold_price()
    if latest_gold is None:
        return

    # Gulf-market owners (SAR/AED/...) are priced from the international spot in
    # their own currency; everyone else keeps the Egyptian dealer price below.
    from core.services.shared.market_profile import is_gulf_user, spot_gold_snapshot

    gulf_snapshot = spot_gold_snapshot(asset.owner, latest_gold) if is_gulf_user(asset.owner) else None
    if gulf_snapshot is not None:
        usd_to_egp = _to_decimal(gulf_snapshot["usd_to_base"])  # purchase-currency units per 1 USD
    else:
        usd_to_egp = _to_decimal(latest_gold.usd_to_egp)
        # The stored rate is EGP per USD. purchase_price is in the owner's base
        # currency, so a non-EGP, non-Gulf owner needs base units per USD instead
        # (otherwise purchase_price_usd = price / EGP-rate is wrong). EGP-base
        # owners keep the exact previous value.
        from core.services.shared.base_currency import get_user_base_code, GOLD_PRICE_CURRENCY
        from core.services.shared.currency_conversion_service import CurrencyConversionService

        owner_base = get_user_base_code(asset.owner)
        if owner_base != GOLD_PRICE_CURRENCY:
            usd_in_base = CurrencyConversionService.get_rates_to_base(owner_base).get("USD")
            usd_to_egp = _to_decimal(usd_in_base) if usd_in_base else Decimal("0")
    if usd_to_egp > 0:
        asset.purchase_usd_rate = usd_to_egp
        asset.purchase_price_usd = _to_decimal(asset.purchase_price) / usd_to_egp

    purity_key = _normalize_gold_purity(details.purity)
    if gulf_snapshot is not None:
        sell_price_per_gram = _to_decimal(gulf_snapshot["carat_" + purity_key])
    else:
        sell_price_per_gram = _gold_sell_price_per_gram(latest_gold, purity_key)
    unit_factor = _gold_unit_factor(details.unit)
    details.market_price = sell_price_per_gram * unit_factor

    cashback_per_gram = _gold_cashback_per_gram(details.purity, owner=asset.owner)
    details.cashback_per_gram = cashback_per_gram
    total_weight_grams = _gold_weight_in_grams(details.weight, details.unit)
    value_in_gold_currency = total_weight_grams * (sell_price_per_gram + cashback_per_gram)

    # Gold prices are always sourced in GOLD_PRICE_CURRENCY (EGP, see
    # base_currency.py). current_market_value must be expressed in the
    # asset owner's own base currency like every other asset's value, so
    # convert here. For an EGP-base owner this is rate=1.000000, i.e. a
    # no-op that reproduces the previous value exactly.
    from core.services.shared.base_currency import get_user_base_code, GOLD_PRICE_CURRENCY
    from core.services.shared.currency_conversion_service import CurrencyConversionService

    base_code = get_user_base_code(asset.owner)
    if gulf_snapshot is not None or base_code == GOLD_PRICE_CURRENCY:
        # Gulf: sell price and cashback are already in the owner's base currency.
        asset.current_market_value = value_in_gold_currency
    else:
        _, asset.current_market_value = CurrencyConversionService.convert_amount(
            value_in_gold_currency, GOLD_PRICE_CURRENCY, base_code
        )
    asset.valuation_source = "Automatic"
    asset.last_valuation_date = timezone.now().date()

    details.save(update_fields=["market_price", "updated_at"])
    asset.save(
        update_fields=[
            "purchase_usd_rate",
            "purchase_price_usd",
            "current_market_value",
            "valuation_source",
            "last_valuation_date",
            "updated_at",
        ]
    )
