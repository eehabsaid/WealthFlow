# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false
"""
Gold decimal/unit/purity conversion helpers.

Split out of the former monolithic gold_sync_service.py (200-line rule).
"""

from decimal import Decimal, InvalidOperation
from core.models import GoldPrice, GoldPuritySetting
from core.constants import GOLD_UNIT_TO_GRAMS


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
