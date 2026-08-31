"""
NOTE: Part of the risk_analysis_service package (split per the >200-line rule).
Shared primitives used across the package: the numeric coercion helper and the
RiskMetric dataclass returned by each _calc_* method in risk_analysis_calc_mixin.py.
"""
from __future__ import annotations

from dataclasses import dataclass


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class RiskMetric:
    id: str
    label_key: str
    score: float
    level: str
    level_key: str
    reason_key: str
    reason_params: dict
