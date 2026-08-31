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

from django.db.models import Max

from core.models import AssetSale, BankCertificate, BankCertificateInterestHistory, _is_certificate_active

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

    def _certificate_events(self, rates: Dict[str, float]) -> List[ForecastEvent]:
        certs = list(BankCertificate.objects.select_related("bank", "currency").all())
        active_certs = [cert for cert in certs if _is_certificate_active(cert)]
        if not active_certs:
            return []

        cert_ids = [cert.id for cert in active_certs]
        history_rows = (
            BankCertificateInterestHistory.objects
            .filter(certificate_id__in=cert_ids)
            .filter(posting_date__lte=self.today)
            .values("certificate_id")
            .annotate(last_posting=Max("posting_date"))
        )
        history_map = {row["certificate_id"]: row["last_posting"] for row in history_rows}

        events: List[ForecastEvent] = []
        for cert in active_certs:
            if not cert.issue_date or not cert.expiry_date:
                continue
            if cert.expiry_date <= self.today:
                continue

            interval = self._interest_service._frequency_interval_months(cert.frequency)
            currency_code = str(getattr(cert.currency, "code", "EGP") or "EGP").upper()
            principal_egp = self._convert_egp(to_float(cert.amount), currency_code, rates)
            interest_period_egp = self._convert_egp(to_float(cert.interest_value), currency_code, rates)
            if interest_period_egp <= 0:
                continue

            maturity_interest_egp = 0.0
            if interval:
                last_posted = cert.last_interest_posted_date
                history_last = history_map.get(cert.id)
                if last_posted and history_last:
                    effective_last = max(last_posted, history_last)
                else:
                    effective_last = last_posted or history_last

                period_index = 1
                due_date = self._interest_service._scheduled_due_date(cert.issue_date, interval, period_index)
                while due_date <= cert.expiry_date and due_date <= self.timeline_end_date:
                    if due_date > self.today and (effective_last is None or due_date > effective_last):
                        if due_date < cert.expiry_date:
                            events.append(
                                ForecastEvent(
                                    event_date=due_date,
                                    event_type="certificate_interest",
                                    amount_egp=interest_period_egp,
                                    meta={"certificate_id": cert.id},
                                )
                            )
                        else:
                            maturity_interest_egp += interest_period_egp
                    period_index += 1
                    due_date = self._interest_service._scheduled_due_date(cert.issue_date, interval, period_index)

            if cert.expiry_date <= self.timeline_end_date:
                events.append(
                    ForecastEvent(
                        event_date=cert.expiry_date,
                        event_type="certificate_maturity",
                        amount_egp=principal_egp + maturity_interest_egp,
                        meta={"certificate_id": cert.id},
                    )
                )

        return events

    def _asset_sale_events(self) -> List[ForecastEvent]:
        sales = (
            AssetSale.objects.select_related("asset")
            .filter(sale_date__gt=self.today, sale_date__lte=self.timeline_end_date, net_sale_amount__gt=0)
            .order_by("sale_date", "id")
        )
        out: List[ForecastEvent] = []
        for sale in sales:
            out.append(
                ForecastEvent(
                    event_date=sale.sale_date,
                    event_type="asset_sale",
                    amount_egp=to_float(sale.net_sale_amount),
                    meta={"asset_id": sale.asset_id},
                )
            )
        return out

    def _build_events(self) -> tuple[List[ForecastEvent], Dict[str, float]]:
        from core.services.salary.salary_service import MONTH_ORDER
        rates = self._rates()
        current_monthly_salary = self._monthly_salary_egp()
        monthly_rental = self._monthly_rental_egp()
        monthly_expense = self._monthly_expense_egp(rates)
        monthly_mortgage = self._monthly_mortgage_installment_egp()

        events: List[ForecastEvent] = []
        for month_end in self._month_end_dates():
            month_name = MONTH_ORDER[month_end.month - 1]
            m_salary = self._monthly_salary_egp(year=month_end.year, month=month_name)
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
