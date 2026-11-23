"""
NOTE: Part of the cash_flow_forecast_service package split (see helpers.py
docstring for the 200-line-per-file convention this package follows).

EventsMixin: walks the forecast horizon month-by-month and generates the
full ForecastEvent list (salary, rental, expenses, mortgage, certificate
interest/maturity, asset sales). Composed onto CashFlowForecastService in
core.py; depends on RatesMixin and RecurringMixin also being present on
the composed class.
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import Dict, List

from core.models import AssetSale

from .certificate_schedule import build_certificate_schedule
from .helpers import ForecastEvent, to_float


class EventsMixin:
    def _add_months(self, base_date: date, months: int) -> date:
        month_index = base_date.month - 1 + months
        year = base_date.year + month_index // 12
        month = month_index % 12 + 1
        day = min(base_date.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    def _month_end_dates(self) -> List[date]:
        current = date(self.today.year, self.today.month, 1)
        out: List[date] = []
        while current <= self.timeline_end_date:
            last_day = calendar.monthrange(current.year, current.month)[1]
            month_end = date(current.year, current.month, last_day)
            if month_end > self.today:
                out.append(month_end)
            current = self._add_months(current, 1)
        return out

    def certificate_schedule(self, until: date | None = None, rates: Dict[str, float] | None = None):
        """Per-certificate interest/maturity items (shared with the Commitments Calendar)."""
        rates = self._rates() if rates is None else rates
        return build_certificate_schedule(
            self.owner, self.today, until or self.timeline_end_date, self._interest_service,
            lambda amount, code: self._convert_base(amount, code, rates),
        )

    def _certificate_events(self, rates: Dict[str, float]) -> List[ForecastEvent]:
        return [
            ForecastEvent(item.event_date, item.event_type, item.amount_base, {"certificate_id": item.certificate.id})
            for item in self.certificate_schedule(rates=rates)
        ]

    def _asset_sale_events(self) -> List[ForecastEvent]:
        sales = (
            AssetSale.objects.select_related("asset")
            .filter(asset__owner=self.owner, sale_date__gt=self.today, sale_date__lte=self.timeline_end_date, net_sale_amount__gt=0)
            .order_by("sale_date", "id")
        )
        out: List[ForecastEvent] = []
        for sale in sales:
            out.append(
                ForecastEvent(
                    event_date=sale.sale_date,
                    event_type="asset_sale",
                    amount_base=to_float(sale.net_sale_amount),
                    meta={"asset_id": sale.asset_id},
                )
            )
        return out

    def _build_events(self) -> tuple[List[ForecastEvent], Dict[str, float]]:
        from core.services.salary.salary_service import MONTH_ORDER
        rates = self._rates()
        current_monthly_salary = self._monthly_salary_base()
        monthly_rental = self._monthly_rental_base()
        monthly_expense = self._monthly_expense_base(rates)
        monthly_mortgage = self._monthly_mortgage_installment_base()

        events: List[ForecastEvent] = []
        for month_end in self._month_end_dates():
            month_name = MONTH_ORDER[month_end.month - 1]
            m_salary = self._monthly_salary_base(year=month_end.year, month=month_name)
            salary_day = self._salary_payment_day(month_end.year, month_end.month)
            salary_date = date(month_end.year, month_end.month, salary_day)
            if m_salary > 0 and self.today < salary_date <= self.timeline_end_date:
                events.append(ForecastEvent(salary_date, "salary", m_salary, {}))
            if monthly_rental > 0:
                events.append(ForecastEvent(month_end, "rental_income", monthly_rental, {}))
            if monthly_expense > 0:
                events.append(ForecastEvent(month_end, "expenses", -monthly_expense, {}))
            if monthly_mortgage > 0:
                events.append(ForecastEvent(month_end, "mortgage_payment", -monthly_mortgage, {}))

        events.extend(self._certificate_events(rates))
        events.extend(self._asset_sale_events())
        events.sort(key=lambda event: (event.event_date, event.event_type))

        return events, {
            "monthly_salary": current_monthly_salary,
            "monthly_rental": monthly_rental,
            "monthly_expense": monthly_expense,
            "monthly_mortgage": monthly_mortgage,
        }
