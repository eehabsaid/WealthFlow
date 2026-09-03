"""Insight and recommendation generation for goal planning."""

from __future__ import annotations

from typing import List

from .context import GoalCalc


class InsightsAndRecommendationsMixin:
    """Generates severity-tagged insights and recommendations from goal state."""

    def _insights(self, goals: List[GoalCalc], summary: dict) -> List[dict]:
        insights: List[dict] = []

        if summary["capacity_slack_egp"] < 0:
            insights.append({
                "key": "goal_planning_insight_capacity_gap",
                "severity": "high",
                "severity_key": "goal_planning_severity_high",
            })

        critical = [g for g in goals if g.status == "critical"]
        if critical:
            insights.append({
                "key": "goal_planning_insight_overdue",
                "severity": "high",
                "severity_key": "goal_planning_severity_high",
            })

        high_risk = [g for g in goals if g.priority == "High" and g.status in ("at_risk", "critical")]
        if high_risk:
            insights.append({
                "key": "goal_planning_insight_high_priority_risk",
                "severity": "medium",
                "severity_key": "goal_planning_severity_medium",
            })

        if summary["overall_progress_pct"] >= 70:
            insights.append({
                "key": "goal_planning_insight_good_progress",
                "severity": "low",
                "severity_key": "goal_planning_severity_low",
            })

        if not insights:
            insights.append({
                "key": "goal_planning_insight_balanced",
                "severity": "info",
                "severity_key": "goal_planning_severity_info",
            })

        return insights[:4]

    def _recommendations(self, goals: List[GoalCalc], summary: dict) -> List[dict]:
        items: List[dict] = []

        if summary["capacity_slack_egp"] < 0:
            items.append({
                "key": "goal_planning_rec_increase_savings",
                "severity": "high",
                "severity_key": "goal_planning_severity_high",
            })

        if any(g.months_left <= 3 and g.status != "achieved" for g in goals):
            items.append({
                "key": "goal_planning_rec_near_deadlines",
                "severity": "medium",
                "severity_key": "goal_planning_severity_medium",
            })

        if any(g.priority == "Low" and g.monthly_required_egp > 0 for g in goals):
            items.append({
                "key": "goal_planning_rec_reprioritize",
                "severity": "info",
                "severity_key": "goal_planning_severity_info",
            })

        if any(g.linked_asset_name and g.status in ("at_risk", "critical") for g in goals):
            items.append({
                "key": "goal_planning_rec_optimize_linked_assets",
                "severity": "low",
                "severity_key": "goal_planning_severity_low",
            })

        if not items:
            items.append({
                "key": "goal_planning_rec_keep_strategy",
                "severity": "low",
                "severity_key": "goal_planning_severity_low",
            })

        return items[:4]
