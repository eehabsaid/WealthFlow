from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Dict, List

from django.db.models import Max

from core.models import (
    AssetMortgage,
    AssetSale,
    BankCertificate,
    BankCertificateInterestHistory,
    Expense,
    SalaryEntry,
    _is_certificate_active,
)
from core.services.certificate_interest_service import CertificateInterestService
from core.services.financial_sync_service import FinancialSyncService
from core.services.net_worth_service import NetWorthService


def _to_decimal(value, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class ForecastEvent:
    event_date: date
    event_type: str
    amount_egp: float
    meta: Dict[str, float | int | str]


class CashFlowForecastService:
    CHECKPOINT_DAYS = [30, 90, 180, 365]

    def __init__(self, today: date | None = None):
        self.today = today or date.today()
        self.horizon_date = self.today + timedelta(days=365)
        self._net_worth_service = NetWorthService()
        self._financial_sync_service = FinancialSyncService()
        self._interest_service = CertificateInterestService()

    def _add_months(self, base_date: date, months: int) -> date:
        month_index = base_date.month - 1 + months
        year = base_date.year + month_index // 12
        month = month_index % 12 + 1
        day = min(base_date.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    def _month_end_dates(self) -> List[date]:
        current = date(self.today.year, self.today.month, 1)
        out: List[date] = []
        while current <= self.horizon_date:
            last_day = calendar.monthrange(current.year, current.month)[1]
            month_end = date(current.year, current.month, last_day)
            if month_end > self.today:
                out.append(min(month_end, self.horizon_date))
            current = self._add_months(current, 1)
        return out

    def _rates(self) -> Dict[str, float]:
        comp = self._net_worth_service.portfolio_components()
        raw_rates = comp.get("rates", {})
        return {str(code or "").upper(): _to_float(value) for code, value in raw_rates.items()}

    def _convert_egp(self, amount: float, currency_code: str, rates: Dict[str, float]) -> float:
        code = str(currency_code or "EGP").upper()
        if code in ("", "EGP"):
            return amount
        return amount * _to_float(rates.get(code))

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
            code = str(getattr(expense.currency, "code", "EGP") or "EGP").upper()
            total += self._convert_egp(_to_float(expense.amount), code, rates)
            active_months.add((expense.year, expense.month))

        month_count = len(active_months) or 1
        return total / month_count

    def _monthly_salary_egp(self) -> float:
        latest_salary = SalaryEntry.objects.filter(paid__gt=0).order_by("-year", "-id").first()
        return _to_float(latest_salary.paid) if latest_salary else 0.0

    def _monthly_rental_egp(self) -> float:
        return _to_float(self._financial_sync_service.period_rental_income_total("month"))

    def _monthly_mortgage_installment_egp(self) -> float:
        mortgages = (
            AssetMortgage.objects.select_related("asset")
            .filter(asset__status="Owned", remaining_balance__gt=0)
            .order_by("id")
        )
        total = 0.0
        for mortgage in mortgages:
            total += _to_float(mortgage.monthly_installment)
        return total

    def _certificate_events(self, rates: Dict[str, float]) -> List[ForecastEvent]:
        certs = list(BankCertificate.objects.select_related("bank", "currency").all())
        active_certs = [cert for cert in certs if _is_certificate_active(cert)]
        if not active_certs:
            return []

        cert_ids = [cert.id for cert in active_certs]
        history_rows = (
            BankCertificateInterestHistory.objects
            .filter(certificate_id__in=cert_ids)
            .values("certificate_id")
            .annotate(last_posting=Max("posting_date"))
        )
        history_map = {row["certificate_id"]: row["last_posting"] for row in history_rows}

        events: List[ForecastEvent] = []
        for cert in active_certs:
            if not cert.issue_date or not cert.expiry_date:
                continue
            if cert.expiry_date <= self.today or cert.expiry_date > self.horizon_date:
                continue

            interval = self._interest_service._frequency_interval_months(cert.frequency)
            currency_code = str(getattr(cert.currency, "code", "EGP") or "EGP").upper()
            principal_egp = self._convert_egp(_to_float(cert.amount), currency_code, rates)
            interest_period_egp = self._convert_egp(_to_float(cert.interest_value), currency_code, rates)

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
                while due_date <= cert.expiry_date and due_date <= self.horizon_date:
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
            .filter(sale_date__gt=self.today, sale_date__lte=self.horizon_date, net_sale_amount__gt=0)
            .order_by("sale_date", "id")
        )
        out: List[ForecastEvent] = []
        for sale in sales:
            out.append(
                ForecastEvent(
                    event_date=sale.sale_date,
                    event_type="asset_sale",
                    amount_egp=_to_float(sale.net_sale_amount),
                    meta={"asset_id": sale.asset_id},
                )
            )
        return out

    def _build_events(self) -> tuple[List[ForecastEvent], Dict[str, float]]:
        rates = self._rates()
        monthly_salary = self._monthly_salary_egp()
        monthly_rental = self._monthly_rental_egp()
        monthly_expense = self._monthly_expense_egp(rates)
        monthly_mortgage = self._monthly_mortgage_installment_egp()

        events: List[ForecastEvent] = []
        for month_end in self._month_end_dates():
            if monthly_salary > 0:
                events.append(ForecastEvent(month_end, "salary", monthly_salary, {}))
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
            "monthly_salary": monthly_salary,
            "monthly_rental": monthly_rental,
            "monthly_expense": monthly_expense,
            "monthly_mortgage": monthly_mortgage,
        }

    def _checkpoints(self, initial_cash: float, events: List[ForecastEvent]) -> Dict[int, float]:
        checkpoint_dates = {days: self.today + timedelta(days=days) for days in self.CHECKPOINT_DAYS}
        result: Dict[int, float] = {}

        running_cash = initial_cash
        idx = 0
        for days in sorted(checkpoint_dates.keys()):
            target = checkpoint_dates[days]
            while idx < len(events) and events[idx].event_date <= target:
                running_cash += events[idx].amount_egp
                idx += 1
            result[days] = running_cash
        return result

    def _timeline(self, initial_cash: float, events: List[ForecastEvent]) -> List[dict]:
        grouped: Dict[str, dict] = {}
        for month_end in self._month_end_dates():
            month_key = f"{month_end.year:04d}-{month_end.month:02d}"
            grouped[month_key] = {
                "month": month_key,
                "events": [],
                "inflow": 0.0,
                "outflow": 0.0,
                "net": 0.0,
                "ending_cash": 0.0,
            }

        running_cash = initial_cash
        for event in events:
            month_key = f"{event.event_date.year:04d}-{event.event_date.month:02d}"
            if month_key not in grouped:
                grouped[month_key] = {
                    "month": month_key,
                    "events": [],
                    "inflow": 0.0,
                    "outflow": 0.0,
                    "net": 0.0,
                    "ending_cash": 0.0,
                }

            item = grouped[month_key]
            event_payload = {
                "date": event.event_date.isoformat(),
                "type": event.event_type,
                "amount": round(event.amount_egp, 2),
            }
            item["events"].append(event_payload)
            if event.amount_egp >= 0:
                item["inflow"] += event.amount_egp
            else:
                item["outflow"] += abs(event.amount_egp)
            item["net"] += event.amount_egp
            running_cash += event.amount_egp
            item["ending_cash"] = running_cash

        timeline = []
        for month_key in sorted(grouped.keys()):
            month_item = grouped[month_key]
            month_item["events"].sort(key=lambda e: (e["date"], e["type"]))
            month_item["inflow"] = round(month_item["inflow"], 2)
            month_item["outflow"] = round(month_item["outflow"], 2)
            month_item["net"] = round(month_item["net"], 2)
            month_item["ending_cash"] = round(month_item["ending_cash"], 2)
            timeline.append(month_item)

        return timeline

    def payload(self) -> dict:
        baseline = self._net_worth_service.certificate_forecast_payload(today=self.today)
        current_cash = _to_float(baseline.get("cash_balance"))

        events, recurring = self._build_events()
        checkpoints = self._checkpoints(current_cash, events)
        timeline = self._timeline(current_cash, events)

        total_increase = sum(event.amount_egp for event in events if event.amount_egp > 0)
        total_decrease = abs(sum(event.amount_egp for event in events if event.amount_egp < 0))
        net_change = total_increase - total_decrease

        largest_event = max(events, key=lambda event: abs(event.amount_egp), default=None)
        largest_expense_event = max(
            [event for event in events if event.amount_egp < 0],
            key=lambda event: abs(event.amount_egp),
            default=None,
        )

        maturity_events = [event for event in events if event.event_type == "certificate_maturity"]
        nearest_maturity = min(maturity_events, key=lambda event: event.event_date, default=None)

        warnings = []
        cash_365 = checkpoints.get(365, current_cash)

        if current_cash > 0 and cash_365 < (current_cash * 0.85):
            warnings.append({"level": "warning", "key": "cash_flow_warning_decrease_significant"})

        if largest_expense_event is not None:
            days_until_expense = (largest_expense_event.event_date - self.today).days
            if days_until_expense <= 60 and abs(largest_expense_event.amount_egp) > max(current_cash * 0.20, 1):
                warnings.append({"level": "danger", "key": "cash_flow_warning_large_expense"})

        if nearest_maturity is not None:
            days_to_maturity = (nearest_maturity.event_date - self.today).days
            if days_to_maturity <= 45:
                warnings.append({"level": "info", "key": "cash_flow_warning_maturity_soon"})

        if not warnings:
            warnings.append({"level": "success", "key": "cash_flow_warning_healthy"})

        summary = {
            "expected_increase": round(total_increase, 2),
            "expected_decrease": round(total_decrease, 2),
            "net_cash_change": round(net_change, 2),
            "largest_cash_event": {
                "type": largest_event.event_type if largest_event else "none",
                "amount": round(_to_float(largest_event.amount_egp) if largest_event else 0.0, 2),
                "date": largest_event.event_date.isoformat() if largest_event else "",
            },
            "nearest_certificate_maturity": {
                "amount": round(_to_float(nearest_maturity.amount_egp) if nearest_maturity else 0.0, 2),
                "date": nearest_maturity.event_date.isoformat() if nearest_maturity else "",
                "days_left": (nearest_maturity.event_date - self.today).days if nearest_maturity else None,
            },
            "largest_planned_expense": {
                "type": largest_expense_event.event_type if largest_expense_event else "none",
                "amount": round(abs(_to_float(largest_expense_event.amount_egp)) if largest_expense_event else 0.0, 2),
                "date": largest_expense_event.event_date.isoformat() if largest_expense_event else "",
            },
        }

        checkpoint_values = {
            "current": round(current_cash, 2),
            "days_30": round(checkpoints.get(30, current_cash), 2),
            "days_90": round(checkpoints.get(90, current_cash), 2),
            "days_180": round(checkpoints.get(180, current_cash), 2),
            "days_365": round(checkpoints.get(365, current_cash), 2),
        }

        return {
            "as_of": self.today.isoformat(),
            "checkpoints": checkpoint_values,
            "timeline": timeline,
            "summary": summary,
            "warnings": warnings,
            "event_types": sorted({event.event_type for event in events}),
            "recurring": {key: round(value, 2) for key, value in recurring.items()},
        }
