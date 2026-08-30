"""Monthly expense baseline, income, and upcoming certificate maturity.

NOTE (200-line file convention): part of the split of
core/services/financial_advisor/portfolio_optimizer_service.py (659 lines).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Tuple

from django.db.models import Sum

from core.models import BankCertificate, Expense, _is_certificate_active

from .shared import _to_float


class ExpenseIncomeMixin:
    def _month_expense_baseline(self) -> Tuple[float, int]:
        start_date = self.today - timedelta(days=180)
        qs = Expense.objects.filter(date__gte=start_date)
        total = _to_float(qs.aggregate(total=Sum("amount_egp")).get("total"))
        active_months = len(set(qs.values_list("year", "month")))
        return total, active_months

    def _monthly_expense_average(self) -> float:
        if hasattr(self, "_monthly_expenses_override") and self._monthly_expenses_override is not None:
            return max(0.0, self._monthly_expenses_override)
        total, active_months = self._month_expense_baseline()
        if active_months > 0:
            return total / active_months
        if total > 0:
            return total / 6.0
        return 0.0

    def _latest_monthly_income(self) -> float:
        from core.services.salary.salary_service import get_current_monthly_salary
        salary_value = get_current_monthly_salary()
        certificate_income = _to_float(self.net_worth.portfolio_components().get("certificate_interest_total_egp"))
        return salary_value + certificate_income

    def _upcoming_certificate_maturity_egp(self, comp: dict, days: int = 90) -> float:
        rates = comp.get("rates", {})
        end_date = self.today + timedelta(days=days)
        total = 0.0

        certs = BankCertificate.objects.select_related("currency").all()
        for cert in certs:
            if not _is_certificate_active(cert) or not cert.expiry_date:
                continue
            if cert.expiry_date < self.today or cert.expiry_date > end_date:
                continue

            code = str(cert.currency.code if cert.currency else "EGP").upper()
            amount = _to_float(cert.amount)
            if code == "EGP":
                total += amount
            else:
                total += amount * _to_float(rates.get(code))

        return total
