"""Budgets page KPI counts, computed server-side (the frontend only displays them)."""
from datetime import date, timedelta

from core.models import Budget, RecurringTransaction
from core.models.budget import RECURRING_DUE_SOON_DAYS
from core.services.budgets.budget_service import BudgetService

class BudgetKpiService:
    @staticmethod
    def get_kpis(owner, ref_date: date = None) -> dict:
        ref_date = ref_date or date.today()
        active = over = 0
        for budget in Budget.objects.filter(owner=owner, is_active=True):
            active += 1
            limit = budget.amount_base or 0
            if limit > 0 and float(BudgetService.compute_spent(budget, ref_date)) / float(limit) * 100 >= 100:
                over += 1
        recurring = RecurringTransaction.objects.filter(
            owner=owner, is_active=True, next_run_date__isnull=False
        )
        horizon = ref_date + timedelta(days=RECURRING_DUE_SOON_DAYS)
        return {
            "active": active,
            "over": over,
            "due_soon": recurring.filter(next_run_date__gte=ref_date, next_run_date__lte=horizon).count(),
            "overdue": recurring.filter(next_run_date__lt=ref_date).count(),
        }
