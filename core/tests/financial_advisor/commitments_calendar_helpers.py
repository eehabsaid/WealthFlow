"""Shared helpers for the calendar-vs-forecast parity tests (not collected as tests)."""

from datetime import date

from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.financial_advisor.commitments_calendar_service import CommitmentsCalendarService

TODAY = date(2026, 11, 22)
START, END = date(2026, 11, 23), date(2027, 11, 22)


def forecast_view(user):
    """Certificate events of the forecast's public payload: {month: (date, total)} and {date: total}."""
    interest, maturity = {}, {}
    for month in CashFlowForecastService(user, today=TODAY).payload()["timeline"]:
        for ev in month["events"]:
            if ev["type"] == "certificate_interest":
                interest[month["month"]] = (ev["date"], ev["amount"])
            elif ev["type"] == "certificate_maturity":
                maturity[ev["date"]] = round(maturity.get(ev["date"], 0) + ev["amount"], 2)
    return interest, maturity


def calendar_events(user):
    events = CommitmentsCalendarService(user, today=TODAY).payload(START, END)["events"]
    return [e for e in events if e["event_type"].startswith("certificate_")]


def calendar_view(events):
    """The same shape as forecast_view, built from calendar events (amount_base)."""
    interest, maturity = {}, {}
    for e in events:
        if e["event_type"] == "certificate_interest":
            month = e["date"][:7]
            prev_date, prev_total = interest.get(month, ("", 0))
            interest[month] = (max(prev_date, e["date"]), round(prev_total + e["amount_base"], 2))
        else:
            maturity[e["date"]] = round(maturity.get(e["date"], 0) + e["amount_base"], 2)
    return interest, maturity
