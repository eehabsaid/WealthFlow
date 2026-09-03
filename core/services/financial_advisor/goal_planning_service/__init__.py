"""
Goal planning service: aggregates goal progress, capacity, and recommendations.

Sibling modules:
- context.py: GoalCalc dataclass carrier, _to_float helper
- calculations.py: GoalCalculationMixin (rates, status, per-goal GoalCalc, monthly capacity)
- summary_and_distribution.py: SummaryAndDistributionMixin (summary, distribution, milestones)
- insights_and_recommendations.py: InsightsAndRecommendationsMixin (insights, recommendations)
"""

from __future__ import annotations

from datetime import date

from core.models import Goal
from core.services.balance.net_worth_service import NetWorthService

from .calculations import GoalCalculationMixin
from .summary_and_distribution import SummaryAndDistributionMixin
from .insights_and_recommendations import InsightsAndRecommendationsMixin

__all__ = ["GoalPlanningService"]


class GoalPlanningService(
    GoalCalculationMixin,
    SummaryAndDistributionMixin,
    InsightsAndRecommendationsMixin,
):
    def __init__(
        self,
        today: date | None = None,
        net_worth_service: NetWorthService | None = None,
        *,
        monthly_capacity_override: float | None = None,
    ):
        self.today = today or date.today()
        self._net_worth_service = net_worth_service or NetWorthService()
        self._capacity_override = monthly_capacity_override

    def payload(self) -> dict:
        rates = self._rates()
        monthly_capacity_egp = self._monthly_capacity_egp()

        goal_rows = list(
            Goal.objects.select_related("currency", "linked_asset").all().order_by("target_date", "id")
        )
        goals = [self._goal_calc(goal, rates, monthly_capacity_egp) for goal in goal_rows]
        goals_sorted = sorted(
            goals,
            key=lambda g: (
                0 if g.priority == "High" else 1 if g.priority == "Medium" else 2,
                g.months_left if g.target_date else 9999,
                -g.remaining_amount_egp,
            ),
        )

        summary = self._summary(goals, monthly_capacity_egp)
        distribution = self._distribution(goals)
        milestones = self._milestones(goals)
        insights = self._insights(goals, summary)
        recommendations = self._recommendations(goals, summary)

        goal_items = [
            {
                "id": g.id,
                "name": g.name,
                "goal_type": g.goal_type,
                "priority": g.priority,
                "priority_key": f"goal_planning_priority_{g.priority.lower()}",
                "target_date": g.target_date,
                "target_amount_egp": g.target_amount_egp,
                "current_saved_egp": g.current_saved_egp,
                "progress_pct": g.progress_pct,
                "remaining_amount_egp": g.remaining_amount_egp,
                "months_left": g.months_left,
                "monthly_required_egp": g.monthly_required_egp,
                "monthly_surplus_egp": g.monthly_surplus_egp,
                "status": g.status,
                "status_key": g.status_key,
                "linked_asset_name": g.linked_asset_name,
            }
            for g in goals_sorted
        ]

        return {
            "as_of": self.today.isoformat(),
            "summary": summary,
            "distribution": distribution,
            "goals": goal_items,
            "milestones": milestones,
            "insights": insights,
            "recommendations": recommendations,
        }
