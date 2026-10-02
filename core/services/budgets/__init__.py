"""Budgets, recurring transactions, and alerts.

Sibling files:
- budget_service.py: Budget CRUD + period-based spend computation against
  Expense.amount_base.
- recurring_service.py: RecurringTransaction CRUD + process_due(), which
  posts due occurrences as real Expense rows via ExpenseService.
- alert_service.py: AlertService.get_alerts(), a live (non-persisted)
  read combining budget-threshold and recurring-due-date alerts.
"""
from .budget_service import BudgetService
from .recurring_service import RecurringService
from .alert_service import AlertService

__all__ = ["BudgetService", "RecurringService", "AlertService"]
