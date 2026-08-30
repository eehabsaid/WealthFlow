"""Presentation-only retirement readiness calculation mixin for
ScenarioPlannerService.

NOTE (200-line file convention): extracted from the original monolithic
core/services/financial_advisor/scenario_planner_service.py (716 lines).
See __init__.py for the full package layout.
"""
from __future__ import annotations

from typing import Any, Dict

from .config import _to_float


class RetirementMixin:
    """Provides _compute_retirement_readiness(); mixed into ScenarioPlannerService."""

    def _compute_retirement_readiness(
        self,
        projected_net_worth_12m: float,
        avg_monthly_expenses: float,
        target_age: int = 60,
    ) -> Dict[str, Any]:
        """Calculates derived presentation-only retirement readiness.

        Formula (standard 4% rule / 25x annual expenses):
            required_nest_egg = (avg_monthly_expenses * 12) * NEST_EGG_MULTIPLIER
            readiness_pct = min(100.0, (projected_net_worth_12m / required_nest_egg) * 100.0)

        This is strictly a display metric — it does NOT alter net worth or forecast.
        """
        nest_egg_multiplier = _to_float(self.config.get("NEST_EGG_MULTIPLIER", 25.0))
        annual_expenses = max(1.0, avg_monthly_expenses * 12.0)
        required_nest_egg = annual_expenses * nest_egg_multiplier

        if required_nest_egg <= 0:
            readiness_pct = 100.0
        else:
            readiness_pct = min(100.0, max(0.0, (projected_net_worth_12m / required_nest_egg) * 100.0))

        return {
            "target_age": target_age,
            "required_nest_egg_egp": round(required_nest_egg, 2),
            "projected_net_worth_egp": round(projected_net_worth_12m, 2),
            "readiness_pct": round(readiness_pct, 1),
            "assumption_note": (
                f"Based on safe withdrawal rate of {int(self.config['DEFAULT_WITHDRAWAL_RATE']*100)}% "
                f"({int(self.config['NEST_EGG_MULTIPLIER'])}x annual expenses of {round(annual_expenses, 2):,} EGP)."
            ),
        }
