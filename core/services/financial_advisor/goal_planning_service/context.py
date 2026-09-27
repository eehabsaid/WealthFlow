"""GoalCalc dataclass carrier and shared numeric helper."""

from __future__ import annotations

from dataclasses import dataclass


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class GoalCalc:
    id: int
    name: str
    goal_type: str
    priority: str
    target_date: str
    target_amount_base: float
    current_saved_base: float
    progress_pct: float
    remaining_amount_base: float
    months_left: int
    monthly_required_base: float
    monthly_surplus_base: float
    status: str
    status_key: str
    linked_asset_name: str
