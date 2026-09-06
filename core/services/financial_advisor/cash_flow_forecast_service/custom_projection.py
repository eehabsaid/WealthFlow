"""
Custom Cash Projection — powers the interactive "what-if" card in the Cash
Flow tab. Lets the user pick a target date, exclude specific recurring
event types (salary, rental, mortgage, certificate interest/maturity, asset
sales), and choose EGP-only vs total-liquid currency scope.

Deliberately reuses CashFlowForecastService's own event-generation
(_build_events) rather than duplicating the recurring-schedule logic, so
this can never silently drift out of sync with the main Cash Flow tab.
Pure Python arithmetic — no LLM involved, so results are always exactly
correct given the same inputs.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import Sum

from core.models import BalanceEntry
from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService

VALID_EVENT_TYPES = {
    "salary", "rental_income", "expenses", "mortgage_payment",
    "certificate_interest", "certificate_maturity", "asset_sale",
}


def _strict_egp_cash_balance() -> float:
    """Literal EGP-currency cash only — excludes other-currency cash and gold."""
    agg = BalanceEntry.objects.filter(
        balance_type__iexact=BalanceEntry.BalanceType.CASH,
        currency__code__iexact="EGP",
    ).aggregate(total=Sum("amount"))
    return float(agg.get("total") or 0)


def compute_custom_cash_projection(
    today: date,
    target_date: date,
    exclude_event_types: list[str] | None = None,
    currency_scope: str = "egp_only",
) -> dict[str, Any]:
    exclude_set = {e for e in (exclude_event_types or []) if e in VALID_EVENT_TYPES}

    svc = CashFlowForecastService(today=today)
    # _build_events() bounds itself by svc.timeline_end_date (read dynamically
    # at call time in events_mixin.py) — extend it here if the requested
    # target_date is further out than the service's default 365-day horizon.
    if target_date > svc.timeline_end_date:
        svc.timeline_end_date = target_date
        svc.horizon_date = target_date

    events, _recurring = svc._build_events()

    if currency_scope == "total_liquid":
        baseline = svc._net_worth_service.certificate_forecast_payload(today=today)
        starting_balance = float(baseline.get("cash_balance") or 0)
    else:
        currency_scope = "egp_only"
        starting_balance = _strict_egp_cash_balance()

    included_events: list[dict[str, Any]] = []
    excluded_events: list[dict[str, Any]] = []
    running_total = starting_balance

    for event in sorted(events, key=lambda e: (e.event_date, e.event_type)):
        if event.event_date > target_date:
            break
        entry = {
            "date": event.event_date.isoformat(),
            "type": event.event_type,
            "amount": round(event.amount_egp, 2),
        }
        if event.event_type in exclude_set:
            excluded_events.append(entry)
            continue
        running_total += event.amount_egp
        included_events.append(entry)

    return {
        "as_of": today.isoformat(),
        "target_date": target_date.isoformat(),
        "currency_scope": currency_scope,
        "excluded_event_types": sorted(exclude_set),
        "starting_balance": round(starting_balance, 2),
        "projected_balance": round(running_total, 2),
        "included_events": included_events,
        "excluded_events": excluded_events,
    }
