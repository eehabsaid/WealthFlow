"""
Small stateless helpers shared across the net_worth_service package.

NOTE (200-line file convention): this module was split out of the original
monolithic core/services/balance/net_worth_service.py (1162 lines) per the
project's 200-line-per-file rule. If this file grows past ~200 lines,
promote related groups of helpers (e.g. formatting vs. conversion) into
their own sibling modules under this same package.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

REAL_ESTATE_ASSET_TYPES = {"Real Estate"}
VEHICLE_ASSET_TYPES = {"Vehicles"}
OTHER_ASSET_TYPES = {"Other Assets"}


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _to_decimal(value, default="0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _normalize_gold_purity(purity_value) -> str:
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


def _fmt_money(value: float) -> str:
    return f"{value:,.2f}"


def _fmt_pct(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"
