"""Allocation value/percentage/status/card computation.

NOTE (200-line file convention): part of the split of
core/services/financial_advisor/portfolio_optimizer_service.py (659 lines).
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .shared import AllocationBand, _to_float


class AllocationMixin:
    def _allocation_values(self, comp: dict) -> Dict[str, float]:
        values = comp.get("allocation_values", {})
        return {
            "cash": _to_float(values.get("type_cash")),
            "certificates": _to_float(values.get("bank_certificates")),
            "gold": _to_float(values.get("type_gold")),
            "real_estate": _to_float(values.get("type_real_estate")),
            "vehicles": _to_float(values.get("type_vehicles")),
            "other_assets": _to_float(values.get("type_other_assets")),
        }

    def _allocation_percentages(self, values: Dict[str, float], total: float) -> Dict[str, float]:
        if total <= 0:
            return {key: 0.0 for key in values}
        return {key: round((value / total) * 100.0, 2) for key, value in values.items()}

    def _status_for_band(self, pct: float, band: AllocationBand) -> Tuple[str, str]:
        if band.min_pct <= pct <= band.max_pct:
            return "good", "portfolio_optimizer_status_in_range"
        distance = 0.0
        if pct < band.min_pct:
            distance = band.min_pct - pct
            status_key = "portfolio_optimizer_status_below_range"
        elif pct > band.max_pct:
            distance = pct - band.max_pct
            status_key = "portfolio_optimizer_status_above_range"
        else:
            status_key = "portfolio_optimizer_status_in_range"
        if distance <= 2.0:
            return "warning", status_key
        return "danger", status_key

    def _allocation_cards(self, values: Dict[str, float], percentages: Dict[str, float]) -> List[dict]:
        cards: List[dict] = []
        for key in self.HOLDING_ORDER:
            band = self.RECOMMENDED_BANDS[key]
            pct = _to_float(percentages.get(key))
            status, status_key = self._status_for_band(pct, band)
            cards.append(
                {
                    "key": key,
                    "label_key": self.ALLOCATION_LABELS[key],
                    "value": round(_to_float(values.get(key)), 2),
                    "percentage": round(pct, 2),
                    "recommended_min": band.min_pct,
                    "recommended_max": band.max_pct,
                    "status": status,
                    "status_key": status_key,
                }
            )
        return cards
