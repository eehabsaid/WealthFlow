from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List

from core.models import Goal
from core.services.balance.net_worth_service import NetWorthService

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
    target_amount_egp: float
    current_saved_egp: float
    progress_pct: float
    remaining_amount_egp: float
    months_left: int
    monthly_required_egp: float
    monthly_surplus_egp: float
    status: str
    status_key: str
    linked_asset_name: str

class GoalPlanningService:
    def __init__(self, today: date | None = None, net_worth_service: NetWorthService | None = None):
        self.today = today or date.today()
        self._net_worth_service = net_worth_service or NetWorthService()

    def _rates(self) -> Dict[str, float]:
        comp = self._net_worth_service.portfolio_components()
        rates = comp.get("rates", {})
        return {str(code or "").upper(): _to_float(value) for code, value in rates.items()}

    def _egp_rate(self, currency_code: str, rates: Dict[str, float]) -> float:
        code = str(currency_code or "EGP").upper()
        if code in ("", "EGP"):
            return 1.0
        return _to_float(rates.get(code)) or 0.0

    def _months_left(self, target: date | None) -> int:
        if not target:
            return 0
        months = (target.year - self.today.year) * 12 + (target.month - self.today.month)
        if target.day > self.today.day:
            months += 1
        return max(0, months)

    def _status_for_goal(self, progress_pct: float, monthly_surplus: float, months_left: int, remaining: float) -> tuple[str, str]:
        if remaining <= 0:
            return "achieved", "goal_planning_status_achieved"
        if months_left <= 0 and remaining > 0:
            return "critical", "goal_planning_status_overdue"
        if monthly_surplus >= 0 and progress_pct >= 65:
            return "on_track", "goal_planning_status_on_track"
        if monthly_surplus >= 0:
            return "watch", "goal_planning_status_needs_attention"
        return "at_risk", "goal_planning_status_at_risk"

    def _priority_weight(self, priority: str) -> int:
        if priority == "High":
            return 3
        if priority == "Medium":
            return 2
        return 1

    def _goal_calc(self, goal: Goal, rates: Dict[str, float], monthly_capacity_egp: float) -> GoalCalc:
        currency_code = getattr(goal.currency, "code", "EGP") or "EGP"
        rate = self._egp_rate(currency_code, rates)

        target_amount_egp = _to_float(goal.target_amount) * rate
        current_saved_egp = _to_float(goal.current_saved_amount) * rate
        remaining = max(0.0, target_amount_egp - current_saved_egp)
        progress_pct = 100.0 if target_amount_egp <= 0 else min(100.0, (current_saved_egp / target_amount_egp) * 100.0)

        months_left = self._months_left(goal.target_date)
        monthly_required = 0.0
        if remaining > 0:
            monthly_required = remaining if months_left <= 0 else (remaining / months_left)

        monthly_surplus = monthly_capacity_egp - monthly_required
        status, status_key = self._status_for_goal(progress_pct, monthly_surplus, months_left, remaining)

        return GoalCalc(
            id=goal.id,
            name=goal.name,
            goal_type=goal.goal_type,
            priority=goal.priority,
            target_date=goal.target_date.isoformat() if goal.target_date else "",
            target_amount_egp=round(target_amount_egp, 2),
            current_saved_egp=round(current_saved_egp, 2),
            progress_pct=round(progress_pct, 2),
            remaining_amount_egp=round(remaining, 2),
            months_left=months_left,
            monthly_required_egp=round(monthly_required, 2),
            monthly_surplus_egp=round(monthly_surplus, 2),
            status=status,
            status_key=status_key,
            linked_asset_name=getattr(goal.linked_asset, "name", "") or "",
        )

    def _monthly_capacity_egp(self) -> float:
        payload = self._net_worth_service.certificate_forecast_payload(today=self.today)
        total_income = _to_float(payload.get("total_monthly_income"))
        monthly_expenses = _to_float(payload.get("monthly_expenses"))
        return round(max(0.0, total_income - monthly_expenses), 2)

    def _summary(self, goals: List[GoalCalc], monthly_capacity_egp: float) -> dict:
        total_goals = len(goals)
        achieved = len([g for g in goals if g.status == "achieved"])
        at_risk = len([g for g in goals if g.status in ("at_risk", "critical")])

        total_target = sum(g.target_amount_egp for g in goals)
        total_saved = sum(g.current_saved_egp for g in goals)
        total_remaining = max(0.0, total_target - total_saved)
        overall_progress = 100.0 if total_target <= 0 else min(100.0, (total_saved / total_target) * 100.0)

        required_monthly = sum(g.monthly_required_egp for g in goals if g.status != "achieved")
        slack = monthly_capacity_egp - required_monthly

        return {
            "total_goals": total_goals,
            "achieved_goals": achieved,
            "at_risk_goals": at_risk,
            "total_target_egp": round(total_target, 2),
            "total_saved_egp": round(total_saved, 2),
            "total_remaining_egp": round(total_remaining, 2),
            "overall_progress_pct": round(overall_progress, 2),
            "monthly_capacity_egp": round(monthly_capacity_egp, 2),
            "required_monthly_egp": round(required_monthly, 2),
            "capacity_slack_egp": round(slack, 2),
        }

    def _distribution(self, goals: List[GoalCalc]) -> dict:
        by_type: Dict[str, float] = {}
        by_priority: Dict[str, int] = {"High": 0, "Medium": 0, "Low": 0}

        for goal in goals:
            by_type[goal.goal_type] = by_type.get(goal.goal_type, 0.0) + goal.target_amount_egp
            by_priority[goal.priority] = by_priority.get(goal.priority, 0) + 1

        type_items = [
            {"label": goal_type, "value_egp": round(value, 2)}
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
            key=lambda g: (g.target_date, -self._priority_weight(g.priority), g.remaining_amount_egp),
        )[:6]
        return [
            {
                "goal_id": g.id,
                "goal_name": g.name,
                "target_date": g.target_date,
                "months_left": g.months_left,
                "remaining_amount_egp": g.remaining_amount_egp,
                "monthly_required_egp": g.monthly_required_egp,
                "priority": g.priority,
                "priority_key": f"goal_planning_priority_{g.priority.lower()}",
            }
            for g in items
        ]

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
