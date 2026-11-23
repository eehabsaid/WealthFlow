"""
Commitments calendar event derivation (core).

Turns existing financial records into calendar events for a date range.
Pure derivation: nothing is posted, no balances are touched.

Event kinds (see service.py docstring):
- actual: a cash movement CashFlowForecastService already models discretely
- expected: a cash movement the forecast models statistically (recurring run-rate)
- informational: a renewal/expiry with no automatic expense

Salary / rental / mortgage event dates and amounts are taken from the
forecast series (public payload) so they never diverge from the forecast.
"""
from __future__ import annotations

import calendar
from datetime import date
from typing import List

from core.models import AssetMortgage, AssetRental
from core.services.salary.salary_service import MONTH_ORDER, get_current_monthly_salary

from .event_shape import _add_months, _in_range, _make, _shared_value
from .events_certificates import CertificateEventsMixin
from .events_renewals import RenewalEventsMixin


class CommitmentsEventsBuilder(CertificateEventsMixin, RenewalEventsMixin):
    def __init__(self, owner, start_date: date, end_date: date, series):
        self.owner = owner
        self.start = start_date
        self.end = end_date
        self.series = series

    def build(self) -> List[dict]:
        events: List[dict] = []
        for method in (
            self._salary_events,
            self._rental_events,
            self._mortgage_events,
            self._certificate_events,
            self._recurring_events,
            self._asset_sale_events,
            self._insurance_events,
            self._vehicle_license_events,
            self._rental_contract_events,
        ):
            events.extend(method())
        events.sort(key=lambda e: (e["date"], e["event_type"], e["source_id"] or 0))
        return events

    def _series_events(self, event_type: str) -> List[dict]:
        return [e for e in self.series.events if e["type"] == event_type]

    def _month_cursor(self):
        month = date(self.start.year, self.start.month, 1)
        while month <= self.end:
            yield month
            month = _add_months(month, 1)

    # Salary: dates/amounts from the forecast series; months outside the
    # forecast horizon use the series salary day + the month's SalaryEntry.
    def _salary_events(self) -> List[dict]:
        salary_series = self._series_events("salary")
        if not salary_series:
            return []
        day = min(e["date"].day for e in salary_series)
        covered = set()
        out = []
        for e in salary_series:
            if _in_range(self.start, self.end, e["date"]):
                out.append(self._salary_event(e["date"], e["amount"]))
                covered.add((e["date"].year, e["date"].month))
        for month in self._month_cursor():
            if (month.year, month.month) in covered:
                continue
            amount = get_current_monthly_salary(self.owner, year=month.year, month=MONTH_ORDER[month.month - 1])
            if amount <= 0:
                continue
            d = date(month.year, month.month, min(day, calendar.monthrange(month.year, month.month)[1]))
            if _in_range(self.start, self.end, d):
                out.append(self._salary_event(d, amount))
        return out

    def _salary_event(self, d: date, amount: float) -> dict:
        return _make(d, "income", "salary", "actual", "commitments_event_salary",
                     amount=amount, amount_base=amount, source="SalaryEntry", status="expected_income")

    # Rental income: forecast series events (month-end convention).
    def _rental_events(self) -> List[dict]:
        rental_series = self._series_events("rental_income")
        if not rental_series or rental_series[0]["amount"] <= 0:
            return []
        amount = rental_series[0]["amount"]
        rentals = list(AssetRental.objects.select_related("asset", "bank").filter(asset__owner=self.owner))
        covered = set()
        out = []
        for e in rental_series:
            if _in_range(self.start, self.end, e["date"]):
                out.append(self._rental_event(e["date"], amount, rentals))
                covered.add((e["date"].year, e["date"].month))
        for month in self._month_cursor():
            if (month.year, month.month) in covered:
                continue
            d = date(month.year, month.month, calendar.monthrange(month.year, month.month)[1])
            if _in_range(self.start, self.end, d):
                out.append(self._rental_event(d, amount, rentals))
        return out

    def _rental_event(self, d: date, amount: float, rentals) -> dict:
        # The forecast amount aggregates every rental: attribute the event to a
        # bank/asset only when that is unambiguous (all records agree).
        return _make(d, "income", "rental_income", "actual", "commitments_event_rental_income",
                     amount=amount, amount_base=amount, source="AssetRental",
                     source_id=rentals[0].asset_id if len(rentals) == 1 else None,
                     bank_id=_shared_value(r.bank_id for r in rentals), status="expected_income",
                     extra={"count": len(rentals)})

    # Mortgage installments: forecast series events (month-end convention).
    def _mortgage_events(self) -> List[dict]:
        mortgage_series = self._series_events("mortgage_payment")
        if not mortgage_series:
            return []
        amount = abs(mortgage_series[0]["amount"])
        if amount <= 0:
            return []
        mortgages = list(AssetMortgage.objects.select_related("asset").filter(
            asset__owner=self.owner, remaining_balance__gt=0))
        covered = set()
        out = []
        for e in mortgage_series:
            if _in_range(self.start, self.end, e["date"]):
                out.append(self._mortgage_event(e["date"], amount, mortgages))
                covered.add((e["date"].year, e["date"].month))
        for month in self._month_cursor():
            if (month.year, month.month) in covered:
                continue
            d = date(month.year, month.month, calendar.monthrange(month.year, month.month)[1])
            if _in_range(self.start, self.end, d):
                out.append(self._mortgage_event(d, amount, mortgages))
        return out

    def _mortgage_event(self, d: date, amount: float, mortgages) -> dict:
        # Aggregated forecast installment: attribute to an asset only if single.
        return _make(d, "expense", "mortgage", "actual", "commitments_event_mortgage",
                     amount=amount, amount_base=amount, source="AssetMortgage",
                     source_id=mortgages[0].asset_id if len(mortgages) == 1 else None,
                     status="active", extra={"count": len(mortgages)})
