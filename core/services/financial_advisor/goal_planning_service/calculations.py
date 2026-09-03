"""Per-goal calculation phase: rates, status classification, GoalCalc construction."""

from __future__ import annotations

from datetime import date
from typing import Dict

from core.models import Goal

from .context import GoalCalc, _to_float


class GoalCalculationMixin:
    """Rate lookups, status classification, and single-goal calculation."""

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
        if self._capacity_override is not None:
            return self._capacity_override
        payload = self._net_worth_service.certificate_forecast_payload(today=self.today)
        total_income = _to_float(payload.get("total_monthly_income"))
        monthly_expenses = _to_float(payload.get("monthly_expenses"))
        return round(max(0.0, total_income - monthly_expenses), 2)
