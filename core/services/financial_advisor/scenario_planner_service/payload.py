"""Orchestrator for ScenarioPlannerService.payload().

Thin coordinator: build baseline -> build scenarios -> assemble final
response. See payload_baseline.py and payload_scenarios.py for the two
computation phases.

NOTE (200-line file convention): extracted from the original monolithic
core/services/financial_advisor/scenario_planner_service.py (716 lines).
See __init__.py for the full package layout.
"""
from __future__ import annotations

from typing import List

from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService

from .payload_baseline import build_baseline
from .payload_scenarios import build_scenarios


class PayloadMixin:
    """Provides payload(); mixed into ScenarioPlannerService."""

    def payload(self, scenario_ids: List[int] | None = None) -> dict:
        """Computes baseline + requested N scenarios for Scenario Planner tab.

        Parameters
        ----------
        scenario_ids : list[int], optional
            List of Scenario model PKs to compare alongside baseline.
        """
        try:
            baseline_dict, ctx = build_baseline(self)
            scenarios_out = build_scenarios(self, ctx, baseline_dict, scenario_ids)

            month_labels = ["Current"] + [pt["month_end"] for pt in ctx.baseline_pts[1:]]

            user_birth_year = None
            if self.user and hasattr(self.user, "profile") and self.user.profile and self.user.profile.birthday:
                user_birth_year = self.user.profile.birthday.year

            return {
                "as_of": self.today.isoformat(),
                "config": self.config,
                "user_birth_year": user_birth_year,
                "recommended_bands": {
                    key: {"min_pct": band.min_pct, "max_pct": band.max_pct}
                    for key, band in PortfolioOptimizerService.RECOMMENDED_BANDS.items()
                },
                "baseline": baseline_dict,
                "scenarios": scenarios_out,
                "month_labels": month_labels,
            }

        except Exception as exc:  # noqa: BLE001
            # Defensive: always return valid JSON payload
            return {
                "as_of": self.today.isoformat(),
                "error": str(exc),
                "config": self.config,
                "recommended_bands": {},
                "baseline": {
                    "id": 0,
                    "name": "Baseline",
                    "description": "Baseline fallback",
                    "net_worth_12m": 0.0,
                    "monthly_cash_flow": 0.0,
                    "total_debt": 0.0,
                    "cash_coverage_months": None,
                    "risk_score": 0.0,
                    "goal_achievement_pct": 0.0,
                    "gold_allocation_pct": 0.0,
                    "retirement_readiness": {},
                    "series": [],
                },
                "scenarios": [],
                "month_labels": [],
            }
