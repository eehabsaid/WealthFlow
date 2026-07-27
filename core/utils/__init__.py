import datetime
from decimal import Decimal
from core.constants import MONTH_ORDER, GOLD_UNIT_TO_GRAMS

def _parse_iso_date(value):
    if not value or str(value).strip() in ("", "None"):
        return None
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value).strip())
    except (ValueError, TypeError):
        return None

def _date_to_iso(dt):
    if isinstance(dt, (datetime.date, datetime.datetime)):
        return dt.isoformat()
    return None

def month_sort_key(entry_dict):
    m_name = entry_dict.get("month", "")
    try:
        return MONTH_ORDER.index(m_name)
    except ValueError:
        return 99

def _to_decimal(value, default="0"):
    if value in (None, ""):
        return Decimal(default)
    try:
        return Decimal(str(value).strip())
    except (ValueError, TypeError):
        return Decimal(default)

def _gold_unit_factor(unit: str) -> Decimal:
    u = str(unit or "").strip().lower()
    return GOLD_UNIT_TO_GRAMS.get(u, Decimal("1"))

def _gold_weight_in_grams(weight_value, unit: str) -> Decimal:
    w = _to_decimal(weight_value)
    factor = _gold_unit_factor(unit)
    return w * factor

def _normalize_gold_purity(purity_value) -> int:
    val = str(purity_value or "").strip().lower()
    if val in ("24", "24k", "24 karat", "24 karat gold"):
        return 24
    if val in ("22", "22k", "22 karat", "22 karat gold"):
        return 22
    if val in ("21", "21k", "21 karat", "21 karat gold"):
        return 21
    if val in ("18", "18k", "18 karat", "18 karat gold"):
        return 18
    # numeric fallback
    digits = "".join(c for c in val if c.isdigit())
    if digits:
        try:
            num = int(digits)
            if num in (18, 21, 22, 24):
                return num
        except ValueError:
            pass
    return 21  # default to 21k in Egypt

def _gold_sell_price_per_gram(purity: int, gold_price_record) -> Decimal:
    if not gold_price_record:
        return Decimal("0")
    if purity == 24:
        return Decimal(str(gold_price_record.carat_24k))
    if purity == 22:
        return Decimal(str(gold_price_record.carat_22k))
    if purity == 21:
        return Decimal(str(gold_price_record.carat_21k))
    if purity == 18:
        return Decimal(str(gold_price_record.carat_18k))
    return Decimal("0")

def _gold_cashback_per_gram(purity: int, gold_price_record) -> Decimal:
    if not gold_price_record:
        return Decimal("0")
    if purity == 24:
        return Decimal(str(gold_price_record.carat_24k_buy or gold_price_record.carat_24k))
    if purity == 22:
        return Decimal(str(gold_price_record.carat_22k_buy or gold_price_record.carat_22k))
    if purity == 21:
        return Decimal(str(gold_price_record.carat_21k_buy or gold_price_record.carat_21k))
    if purity == 18:
        return Decimal(str(gold_price_record.carat_18k_buy or gold_price_record.carat_18k))
    return Decimal("0")

from core.utils.date_formatter import format_date

__all__ = [
    "datetime",
    "Decimal",
    "MONTH_ORDER",
    "GOLD_UNIT_TO_GRAMS",
    "format_date",
]
