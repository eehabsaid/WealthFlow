"""
NOTE: Part of the cash_flow_forecast_service package split (see helpers.py
docstring for the 200-line-per-file convention this package follows).

RecurringMixin: derives the recurring monthly cash-flow figures (expense
run-rate, salary, rental income, mortgage installments) and the salary
payment-day logic driven by ReminderRule config. Composed onto
CashFlowForecastService in core.py.
"""

from __future__ import annotations

import calendar
from datetime import timedelta
from typing import Dict

from core.models import AssetMortgage, Expense, ReminderRule

from .helpers import to_float


class RecurringMixin:
    def _monthly_expense_egp(self, rates: Dict[str, float]) -> float:
        last_90 = self.today - timedelta(days=90)
        expenses = list(
            Expense.objects.select_related("currency")
            .filter(date__gte=last_90)
            .order_by("date")
        )
        if not expenses:
            return 0.0

        total = 0.0
        active_months = set()
        for expense in expenses:
            total += to_float(expense.amount_egp)
            active_months.add((expense.year, expense.month))

        month_count = len(active_months) or 1
        return total / month_count

    def _monthly_salary_egp(self, year: int = None, month: str = None) -> float:
        from core.services.salary.salary_service import get_current_monthly_salary
        return get_current_monthly_salary(year=year, month=month)

    def _get_salary_rule(self):
        if self._salary_rule is not None:
            return self._salary_rule

        # Prefer explicit salary-day reminder config used by the Reminder settings page.
        rule = ReminderRule.objects.filter(is_active=True, rule_type="salary_day").order_by("id").first()
        if rule is None:
            # Fallback to salary-unpaid trigger config if salary-day rule is not present.
            rule = ReminderRule.objects.filter(is_active=True, rule_type="salary_unpaid").order_by("id").first()

        self._salary_rule = rule
        return rule

    def _salary_payment_day(self, year: int, month: int) -> int:
        last_day = calendar.monthrange(year, month)[1]
        rule = self._get_salary_rule()
        if rule is None:
            # Keep historical default when no reminder rule is configured.
            return min(25, last_day)

        trigger = str(rule.salary_trigger or "").strip().lower()
        trigger_value = int(rule.salary_day or 1)

        if trigger == "day_of_month":
            return min(max(1, trigger_value), last_day)
        if trigger == "days_before_eom":
            return max(1, last_day - max(0, trigger_value))
        if trigger == "days_after_som":
            return min(max(1, trigger_value + 1), last_day)

        return min(max(1, trigger_value), last_day)

    def _monthly_rental_egp(self) -> float:
        return to_float(self._financial_sync_service.period_rental_income_total("month"))

    def _monthly_mortgage_installment_egp(self) -> float:
        mortgages = (
            AssetMortgage.objects.select_related("asset")
            .filter(asset__status="Owned", remaining_balance__gt=0)
            .order_by("id")
        )
        total = 0.0
        for mortgage in mortgages:
            total += to_float(mortgage.monthly_installment)
        return total
