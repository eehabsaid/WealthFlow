# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false
"""
Gold asset pricing refresh and balance-sync business logic.

Split out of the former monolithic gold_sync_service.py (200-line rule).
"""

from decimal import Decimal
from django.utils import timezone
from core.models import (
    BalanceEntry,
    Currency,
    FixedAsset,
    GoldDetails,
)
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

    usd_to_egp = _to_decimal(latest_gold.usd_to_egp)
    if usd_to_egp > 0:
        asset.purchase_usd_rate = usd_to_egp
        asset.purchase_price_usd = _to_decimal(asset.purchase_price) / usd_to_egp

    purity_key = _normalize_gold_purity(details.purity)
    sell_price_per_gram = _gold_sell_price_per_gram(latest_gold, purity_key)
    unit_factor = _gold_unit_factor(details.unit)
    details.market_price = sell_price_per_gram * unit_factor

    cashback_per_gram = _gold_cashback_per_gram(details.purity, owner=asset.owner)
    details.cashback_per_gram = cashback_per_gram
    total_weight_grams = _gold_weight_in_grams(details.weight, details.unit)
    asset.current_market_value = total_weight_grams * (sell_price_per_gram + cashback_per_gram)
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


def _sync_gold_balance_from_assets(owner):
    gold_currency = Currency.objects.filter(code__iexact="gold", owner=owner).first()
    if not gold_currency:
        return

    gold_assets = (
        FixedAsset.objects.filter(owner=owner, asset_type__in=GOLD_ASSET_TYPES, status="Owned")
        .select_related("gold_details")
        .order_by("id")
    )

    grams_by_purity = {}
    for asset in gold_assets:
        details = getattr(asset, "gold_details", None)
        if details is None:
            continue
        grams = _gold_weight_in_grams(details.weight, details.unit)
        purity_key = _normalize_gold_purity(details.purity)
        grams_by_purity[purity_key] = grams_by_purity.get(purity_key, Decimal("0")) + grams

    balance_qs = BalanceEntry.objects.filter(
        owner=owner,
        balance_type=BalanceEntry.BalanceType.GOLD,
        currency_id=gold_currency.id,
    ).order_by("id")

    if not grams_by_purity:
        balance_qs.delete()
        return

    existing_by_purity = {str(e.purity or "").lower(): e for e in balance_qs}
    used_ids = []
    for purity_key, grams in grams_by_purity.items():
        entry = existing_by_purity.get(purity_key)
        title = f"{gold_currency.name or 'Gold'} {purity_key.upper()}"
        amount = grams.quantize(Decimal("0.01"))

        if entry:
            entry.title = title
            entry.bank = None
            entry.amount = amount
            entry.notes = ""
            entry.purity = purity_key
            entry.save()
            used_ids.append(entry.id)
        else:
            created = BalanceEntry.objects.create(
                owner=owner,
                title=title,
                balance_type=BalanceEntry.BalanceType.GOLD,
                bank=None,
                currency_id=gold_currency.id,
                purity=purity_key,
                amount=amount,
                notes="",
            )
            used_ids.append(created.id)

    balance_qs.exclude(id__in=used_ids).delete()


def _refresh_all_gold_assets_from_live_prices():
    """System-wide: a live gold price change affects every user's gold
    holdings, so this refreshes each owner's assets and gold BalanceEntry
    in turn (never mixing one owner's grams into another's balance)."""
    from django.contrib.auth import get_user_model

    latest_gold = _latest_gold_price()
    if latest_gold is None:
        return

    gold_assets = FixedAsset.objects.filter(asset_type__in=GOLD_ASSET_TYPES).select_related("gold_details")
    owner_ids = set()
    for asset in gold_assets:
        details = getattr(asset, "gold_details", None)
        if details is None:
            continue
        _refresh_gold_asset_pricing(asset, details, latest_gold)
        if asset.owner_id:
            owner_ids.add(asset.owner_id)

    User = get_user_model()
    for owner in User.objects.filter(id__in=owner_ids):
        _sync_gold_balance_from_assets(owner)


def _sync_gold_details(asset, details_data):
    if asset.asset_type not in GOLD_ASSET_TYPES or not details_data:
        if hasattr(asset, "gold_details"):
            asset.gold_details.delete()
        return

    details_obj, _ = GoldDetails.objects.update_or_create(
        asset=asset,
        defaults={
            "gold_type": details_data.get("gold_type", ""),
            "purity": _normalize_gold_purity(details_data.get("purity", "")),
            "weight": details_data.get("weight", 0),
            "unit": details_data.get("unit", "gram"),
            "cashback_per_gram": _gold_cashback_per_gram(details_data.get("purity", ""), owner=asset.owner),
            "purchase_weight": details_data.get("purchase_weight", 0),
        },
    )

    _refresh_gold_asset_pricing(asset, details_obj)
