"""
NOTE: Package-folder split of the former flat
core/services/financial_advisor/cash_flow_forecast_service.py (482 lines),
broken up per the project's 200-line-per-file convention. Promote any
sibling file back to its own subfolder if it grows past 200 lines.

This file holds the small, dependency-free primitives shared across the
rest of the package: numeric coercion helpers and the ForecastEvent
dataclass produced by the event-generation mixin and consumed by the
timeline mixin and summary phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict


def to_decimal(value, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class ForecastEvent:
    event_date: date
    event_type: str
    amount_egp: float
    meta: Dict[str, float | int | str]
