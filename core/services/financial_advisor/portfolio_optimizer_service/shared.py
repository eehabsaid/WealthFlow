"""Shared primitives for the portfolio optimizer package.

NOTE (200-line file convention): part of the split of
core/services/financial_advisor/portfolio_optimizer_service.py (659 lines).
Kept separate from __init__.py so mixin modules can import `_to_float` and
`AllocationBand` without creating a circular import with the umbrella
__init__.py (which imports the mixins).
"""
from __future__ import annotations

from dataclasses import dataclass


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


@dataclass(frozen=True)
class AllocationBand:
    min_pct: float
    max_pct: float
