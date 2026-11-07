"""Income figures for the Expenses Report: one calendar month = that month's own values only."""

import calendar
import datetime
from decimal import Decimal

from django.db.models import Sum

from core.models import BankCertificate, MonthlyIncomeAdjustment, SalaryEntry
from core.services.balance.financial_sync_service import FinancialSyncService

MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]


def _certificate_in_period(certificate, start_date, end_date):
    if certificate.issue_date and certificate.issue_date > end_date:
        return False
    if certificate.expiry_date and certificate.expiry_date < start_date:
        return False
    return True


def _interest_for_period(owner, start_date, end_date):
    return sum(
        float(c.interest_value or 0)
        for c in BankCertificate.objects.filter(owner=owner, status__iexact="Active")
        if _certificate_in_period(c, start_date, end_date)
    )


def _months_between(start, end):
    """(year, month) pairs of every calendar month the range touches."""
    pairs, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        pairs.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return pairs


def _summary(salary, interest, rental, extra):
    salary, rental = float(salary or 0), float(rental or 0)
    return {
        "total_income": salary + interest + rental + extra,
        "total_salary": salary,
        "total_interest": interest,
        "total_rental_income": rental,
        "manual_income": extra,
    }


def _range_summary(owner, start, end):
    """Income for a custom date range: every month the range touches, interest for certificates active in it."""
    rental_service = FinancialSyncService()
    salary, rental, extra = 0, Decimal("0"), 0.0
    for y, m in _months_between(start, end):
        salary += SalaryEntry.objects.filter(
            company__owner=owner, year=y, month__iexact=MONTH_NAMES[m - 1]
        ).aggregate(total=Sum("paid"))["total"] or 0
        rental += rental_service.rental_income_for_month(owner, y, m)
        extra += manual_income(owner, y, m)
    return _summary(salary, _interest_for_period(owner, start, end), rental, extra)


def manual_income(owner, year, month=None):
    qs = MonthlyIncomeAdjustment.objects.filter(owner=owner, year=year)
    if month:
        qs = qs.filter(month=month)
    return float(qs.aggregate(t=Sum("amount"))["t"] or 0)


def build_income_summary(owner, year=None, month=None, start=None, end=None):
    """Return the income_summary dict. start+end -> that date range; month -> that month only;
    year -> whole year; nothing -> current month."""
    if start and end:
        return _range_summary(owner, start, end)
    today = datetime.date.today()
    if not month and not year:
        year, month = today.year, today.month
    rental_service = FinancialSyncService()

    if month:
        year, month = int(year or today.year), int(month)
        start = datetime.date(year, month, 1)
        end = datetime.date(year, month, calendar.monthrange(year, month)[1])
        salary = SalaryEntry.objects.filter(
            company__owner=owner, year=year, month__iexact=MONTH_NAMES[month - 1]
        ).aggregate(total=Sum("paid"))["total"]
        rental = rental_service.rental_income_for_month(owner, year, month)
        extra = manual_income(owner, year, month)
    else:
        year = int(year)
        start, end = datetime.date(year, 1, 1), datetime.date(year, 12, 31)
        salary = SalaryEntry.objects.filter(company__owner=owner, year=year).aggregate(total=Sum("paid"))["total"]
        rental = sum(
            (rental_service.rental_income_for_month(owner, year, m) for m in range(1, 13)), Decimal("0")
        )
        extra = manual_income(owner, year)

    return _summary(salary, _interest_for_period(owner, start, end), rental, extra)
