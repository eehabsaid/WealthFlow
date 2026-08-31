"""
NOTE: Part of the cash_flow_forecast_service package split (see helpers.py
docstring for the 200-line-per-file convention this package follows).

core.py: CashFlowForecastService — composes RatesMixin, RecurringMixin,
EventsMixin and TimelineMixin, and orchestrates payload() using the
standalone summary_phase functions. This is the sole class external
callers instantiate; import path is unchanged via __init__.py.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from core.services.certificate.certificate_interest_service import CertificateInterestService
from core.services.balance.financial_sync_service import FinancialSyncService
from core.services.balance.net_worth_service import NetWorthService

from .events_mixin import EventsMixin
from .helpers import to_float
from .rates_mixin import RatesMixin
from .recurring_mixin import RecurringMixin
from .summary_phase import (
    build_summary,
    build_warnings,
    largest_expense_event,
    largest_positive_event,
    nearest_maturity_event,
)
from .timeline_mixin import TimelineMixin


class CashFlowForecastService(RatesMixin, RecurringMixin, EventsMixin, TimelineMixin):
    CHECKPOINT_DAYS = [30, 90, 180, 365]

    def __init__(self, today: date | None = None, net_worth_service: NetWorthService | None = None):
        self.today = today or date.today()
        self.horizon_date = self.today + timedelta(days=365)
        self.timeline_end_date = date(
            self.horizon_date.year,
            self.horizon_date.month,
            calendar.monthrange(self.horizon_date.year, self.horizon_date.month)[1],
        )
        self._net_worth_service = net_worth_service or NetWorthService()
        self._financial_sync_service = FinancialSyncService()
        self._interest_service = CertificateInterestService()
        self._salary_rule = None

    def payload(self) -> dict:
        baseline = self._net_worth_service.certificate_forecast_payload(today=self.today)
        current_cash = to_float(baseline.get("cash_balance"))

        events, recurring = self._build_events()
        checkpoints = self._checkpoints(current_cash, events)
        timeline = self._timeline(current_cash, events)
        timeline_events = self._timeline_events(timeline)
        month_based_checkpoints = self._month_based_checkpoints(current_cash, timeline)

        positive_event = largest_positive_event(timeline_events)
        expense_event = largest_expense_event(timeline_events)
        maturity_event = nearest_maturity_event(timeline_events)

        cash_365 = checkpoints.get(365, current_cash)
        summary = build_summary(timeline_events, positive_event, expense_event, maturity_event, self.today)
        warnings = build_warnings(current_cash, cash_365, expense_event, maturity_event, self.today)

        return {
            "as_of": self.today.isoformat(),
            "checkpoints": month_based_checkpoints,
            "day_checkpoints": {
                "days_30": round(checkpoints.get(30, current_cash), 2),
                "days_90": round(checkpoints.get(90, current_cash), 2),
                "days_180": round(checkpoints.get(180, current_cash), 2),
                "days_365": round(checkpoints.get(365, current_cash), 2),
            },
            "timeline": timeline,
            "summary": summary,
            "warnings": warnings,
            "event_types": sorted({event.event_type for event in events}),
            "recurring": {key: round(value, 2) for key, value in recurring.items()},
        }
