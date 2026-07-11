# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from decimal import Decimal, InvalidOperation
from django.utils import timezone
from core.models import (
    BalanceEntry,
    GoldPrice,
    Currency,
    FixedAsset,
    GoldDetails,
    GoldPuritySetting,

)
from core.constants import (
    GOLD_ASSET_TYPES,
    GOLD_UNIT_TO_GRAMS,
)

def _to_decimal(value, default="0"):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)

def _gold_unit_factor(unit_value):
    normalized = str(unit_value or "gram").strip().lower()
    return GOLD_UNIT_TO_GRAMS.get(normalized, Decimal("1"))

def _gold_weight_in_grams(weight_value, unit_value):
    return _to_decimal(weight_value) * _gold_unit_factor(unit_value)

def _normalize_gold_purity(purity_value):
    text = str(purity_value or "").strip().lower()
    if "24" in text or "999" in text:
        return "24k"
    if "22" in text or "916" in text:
        return "22k"
    if "21" in text or "875" in text:
        return "21k"
    if "18" in text or "750" in text:
        return "18k"
    return "24k"

def _gold_sell_price_per_gram(latest_gold_price, purity_key):
    price_map = {
        "24k": _to_decimal(latest_gold_price.carat_24k),
        "22k": _to_decimal(latest_gold_price.carat_22k),
        "21k": _to_decimal(latest_gold_price.carat_21k),
        "18k": _to_decimal(latest_gold_price.carat_18k),
    }
    return price_map.get(purity_key, price_map["24k"])

def _gold_cashback_per_gram(purity_value):
    key = _normalize_gold_purity(purity_value)
    setting = GoldPuritySetting.objects.filter(key=key, is_active=True).first()
    if not setting:
        return Decimal("0")
    return _to_decimal(setting.cashback_per_gram)

def _latest_gold_price():
    return GoldPrice.objects.order_by("-fetched_at").first()

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

    cashback_per_gram = _gold_cashback_per_gram(details.purity)
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

def _sync_gold_balance_from_assets():
    gold_currency = Currency.objects.filter(code__iexact="gold").first()
    if not gold_currency:
        return

    gold_assets = (
        FixedAsset.objects.filter(asset_type__in=GOLD_ASSET_TYPES, status="Owned")
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
    latest_gold = _latest_gold_price()
    if latest_gold is None:
        return

    gold_assets = FixedAsset.objects.filter(asset_type__in=GOLD_ASSET_TYPES).select_related("gold_details")
    for asset in gold_assets:
        details = getattr(asset, "gold_details", None)
        if details is None:
            continue
        _refresh_gold_asset_pricing(asset, details, latest_gold)

    _sync_gold_balance_from_assets()

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
            "cashback_per_gram": _gold_cashback_per_gram(details_data.get("purity", "")),
            "purchase_weight": details_data.get("purchase_weight", 0),
        },
    )

    _refresh_gold_asset_pricing(asset, details_obj)

