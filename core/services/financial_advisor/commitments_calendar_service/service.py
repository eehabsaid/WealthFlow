"""
CommitmentsCalendarService — orchestrates event derivation and the
forecast-anchored liquidity analysis for a date range. Read-only: no
posting, no balance changes.

Settings:
- commitments_concentration_window_days (AppSettings, per-user, default 30,
  valid range 1-90) — the N-day window used for concentration analysis.
  Configured on the Reminders settings tab.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from core.constants.user_scoped_settings import INTEGER_SETTING_RANGES
from core.models import AppSettings, Bank
from core.services.shared.base_currency import get_user_base_code
from core.services.shared.currency_conversion_service import CurrencyConversionService

from .events import CommitmentsEventsBuilder
from .liquidity import ForecastSeries, build_analysis

WINDOW_KEY = "commitments_concentration_window_days"
WINDOW_DEFAULT = 30
WINDOW_MIN, WINDOW_MAX = INTEGER_SETTING_RANGES[WINDOW_KEY]

WEEK_START_KEY = "commitments_week_start_day"
WEEK_START_DEFAULT = 0  # Sunday; values follow JavaScript getDay(): 0 = Sunday ... 6 = Saturday
WEEK_START_MIN, WEEK_START_MAX = INTEGER_SETTING_RANGES[WEEK_START_KEY]


def resolve_window_days(owner) -> int:
    raw = str(AppSettings.get(WINDOW_KEY, str(WINDOW_DEFAULT), user=owner) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        return WINDOW_DEFAULT
    return min(max(value, WINDOW_MIN), WINDOW_MAX)


def resolve_week_start_day(owner) -> int:
    raw = str(AppSettings.get(WEEK_START_KEY, str(WEEK_START_DEFAULT), user=owner) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        return WEEK_START_DEFAULT
    return value if WEEK_START_MIN <= value <= WEEK_START_MAX else WEEK_START_DEFAULT


class CommitmentsCalendarService:
    MAX_RANGE_DAYS = 366

    def __init__(self, owner, today: Optional[date] = None):
        self.owner = owner
        self.today = today or date.today()

    def payload(
        self,
        start_date: date,
        end_date: date,
        category: Optional[str] = None,
        bank_id: Optional[int] = None,
    ) -> dict:
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        if (end_date - start_date).days > self.MAX_RANGE_DAYS:
            raise ValueError(f"date range exceeds {self.MAX_RANGE_DAYS} days")

        series = ForecastSeries(self.owner, self.today)
        events = CommitmentsEventsBuilder(self.owner, start_date, end_date, series).build()
        self._fill_amount_base(events)
        window_days = resolve_window_days(self.owner)
        analysis = build_analysis(events, window_days, series, get_user_base_code(self.owner))

        if category:
            events = [e for e in events if e["category"] == category]
        if bank_id:
            events = [e for e in events if e["bank_id"] == bank_id]

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "events": events,
            "analysis": analysis,
            "filters": {
                "categories": ["income", "expense", "renewal"],
                "banks": [{"id": b.id, "name": b.name} for b in Bank.objects.filter(owner=self.owner)],
            },
            "settings": {"concentration_window_days": window_days, "week_start_day": resolve_week_start_day(self.owner)},
        }

    def _fill_amount_base(self, events) -> None:
        base_code = get_user_base_code(self.owner)
        for e in events:
            if e["amount_base"] is not None or not e["currency_code"]:
                continue
            if e["currency_code"].upper() == base_code:
                e["amount_base"] = e["amount"]
                continue
            try:
                rate = float(CurrencyConversionService.strict_rate(e["currency_code"], base_code))
            except ValueError:
                continue  # no stored rate: leave amount_base null, UI shows the original amount only
            e["amount_base"] = round(e["amount"] * rate, 2)
