"""Budget and recurring-transaction alerts, computed on demand.

Deliberately not persisted: alerts here are a live read of current state
(today's spend vs. threshold, upcoming due dates) rather than a fired/ack
notification log, so there's nothing to go stale or need cleanup.
"""
from datetime import date, timedelta

from core.models import Budget, RecurringTransaction
from core.services.budgets.budget_service import BudgetService

UPCOMING_RECURRING_DAYS = 3


class AlertService:
    @staticmethod
    def get_alerts(owner, ref_date: date = None) -> list:
        ref_date = ref_date or date.today()
        alerts = []

        for budget in Budget.objects.filter(owner=owner, is_active=True).select_related("category"):
            spent = BudgetService.compute_spent(budget, ref_date)
            limit = budget.amount_base or 0
            if limit <= 0:
                continue
            percent = float(spent) / float(limit) * 100
            if percent >= 100:
                alerts.append({
                    "type": "budget_exceeded",
                    "budget_id": budget.id,
                    "budget_name": budget.name,
                    "percent_used": round(percent, 1),
                })
            elif percent >= budget.alert_threshold_percent:
                alerts.append({
                    "type": "budget_threshold",
                    "budget_id": budget.id,
                    "budget_name": budget.name,
                    "percent_used": round(percent, 1),
                    "threshold": budget.alert_threshold_percent,
                })

        horizon = ref_date + timedelta(days=UPCOMING_RECURRING_DAYS)
        due_soon = RecurringTransaction.objects.filter(
            owner=owner, is_active=True, next_run_date__gte=ref_date, next_run_date__lte=horizon
        )
        for rec in due_soon:
            alerts.append({
                "type": "recurring_due_soon",
                "recurring_id": rec.id,
                "recurring_name": rec.name,
                "next_run_date": rec.next_run_date.isoformat(),
                "amount": float(rec.amount),
            })

        overdue = RecurringTransaction.objects.filter(
            owner=owner, is_active=True, next_run_date__lt=ref_date
        )
        for rec in overdue:
            alerts.append({
                "type": "recurring_overdue",
                "recurring_id": rec.id,
                "recurring_name": rec.name,
                "next_run_date": rec.next_run_date.isoformat(),
                "amount": float(rec.amount),
            })

        return alerts
