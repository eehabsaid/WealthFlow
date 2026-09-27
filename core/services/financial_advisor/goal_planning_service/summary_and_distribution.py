"""Aggregate summary, type/priority distribution, and upcoming milestones."""

from __future__ import annotations

from typing import Dict, List

from .context import GoalCalc


class SummaryAndDistributionMixin:
    """Portfolio-level summary, distribution breakdowns, and milestone list."""

    def _summary(self, goals: List[GoalCalc], monthly_capacity_base: float) -> dict:
        total_goals = len(goals)
        achieved = len([g for g in goals if g.status == "achieved"])
        at_risk = len([g for g in goals if g.status in ("at_risk", "critical")])

        total_target = sum(g.target_amount_base for g in goals)
        total_saved = sum(g.current_saved_base for g in goals)
        total_remaining = max(0.0, total_target - total_saved)
        overall_progress = 100.0 if total_target <= 0 else min(100.0, (total_saved / total_target) * 100.0)

        required_monthly = sum(g.monthly_required_base for g in goals if g.status != "achieved")
        slack = monthly_capacity_base - required_monthly

        return {
            "total_goals": total_goals,
            "achieved_goals": achieved,
            "at_risk_goals": at_risk,
            "total_target_base": round(total_target, 2),
            "total_saved_base": round(total_saved, 2),
            "total_remaining_base": round(total_remaining, 2),
            "overall_progress_pct": round(overall_progress, 2),
            "monthly_capacity_base": round(monthly_capacity_base, 2),
            "required_monthly_base": round(required_monthly, 2),
            "capacity_slack_base": round(slack, 2),
        }

    def _distribution(self, goals: List[GoalCalc]) -> dict:
        by_type: Dict[str, float] = {}
        by_priority: Dict[str, int] = {"High": 0, "Medium": 0, "Low": 0}

        for goal in goals:
            by_type[goal.goal_type] = by_type.get(goal.goal_type, 0.0) + goal.target_amount_base
            by_priority[goal.priority] = by_priority.get(goal.priority, 0) + 1

        type_items = [
            {"label": goal_type, "value_base": round(value, 2)}
            for goal_type, value in sorted(by_type.items(), key=lambda item: item[1], reverse=True)
        ]

        priority_items = [
            {
                "priority": pr,
                "count": by_priority.get(pr, 0),
                "label_key": f"goal_planning_priority_{pr.lower()}",
            }
            for pr in ("High", "Medium", "Low")
        ]

        return {
            "by_type": type_items,
            "by_priority": priority_items,
        }

    def _milestones(self, goals: List[GoalCalc]) -> List[dict]:
        items = sorted(
            [g for g in goals if g.status != "achieved" and g.target_date],
            key=lambda g: (g.target_date, -self._priority_weight(g.priority), g.remaining_amount_base),
        )[:6]
        return [
            {
                "goal_id": g.id,
                "goal_name": g.name,
                "target_date": g.target_date,
                "months_left": g.months_left,
                "remaining_amount_base": g.remaining_amount_base,
                "monthly_required_base": g.monthly_required_base,
                "priority": g.priority,
                "priority_key": f"goal_planning_priority_{g.priority.lower()}",
            }
            for g in items
        ]
