"""
NOTE: Part of the cash_flow_forecast_service package split (see helpers.py
docstring for the 200-line-per-file convention this package follows).

summary_phase: standalone phase functions (no class state) that turn the
flattened timeline_events/checkpoints produced by TimelineMixin into the
payload's "summary" and "warnings" blocks. Kept free of self/mixin state
so they're independently testable; called from core.py's payload().
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from .helpers import to_float


def largest_positive_event(timeline_events: List[dict]) -> Optional[dict]:
    return max(
        [event for event in timeline_events if event["amount"] > 0],
        key=lambda event: event["amount"],
        default=None,
    )


def largest_expense_event(timeline_events: List[dict]) -> Optional[dict]:
    return max(
        [event for event in timeline_events if event["amount"] < 0],
        key=lambda event: abs(event["amount"]),
        default=None,
    )


def nearest_maturity_event(timeline_events: List[dict]) -> Optional[dict]:
    maturity_events = [event for event in timeline_events if event["type"] == "certificate_maturity"]
    return min(maturity_events, key=lambda event: event["date"], default=None)


def build_summary(timeline_events: List[dict], positive_event: Optional[dict],
                   expense_event: Optional[dict], maturity_event: Optional[dict], today: date) -> dict:
    total_increase = sum(event["amount"] for event in timeline_events if event["amount"] > 0)
    total_decrease = abs(sum(event["amount"] for event in timeline_events if event["amount"] < 0))
    net_change = total_increase - total_decrease

    return {
        "expected_increase": round(total_increase, 2),
        "expected_decrease": round(total_decrease, 2),
        "net_cash_change": round(net_change, 2),
        "largest_cash_event": {
            "type": positive_event["type"] if positive_event else "none",
            "amount": round(to_float(positive_event["amount"]) if positive_event else 0.0, 2),
            "date": positive_event["date"] if positive_event else "",
        },
        "nearest_certificate_maturity": {
            "amount": round(to_float(maturity_event["amount"]) if maturity_event else 0.0, 2),
            "date": maturity_event["date"] if maturity_event else "",
            "days_left": (date.fromisoformat(maturity_event["date"]) - today).days if maturity_event else None,
        },
        "largest_planned_expense": {
            "type": expense_event["type"] if expense_event else "none",
            "amount": round(abs(to_float(expense_event["amount"])) if expense_event else 0.0, 2),
            "date": expense_event["date"] if expense_event else "",
        },
    }


def build_warnings(current_cash: float, cash_365: float, expense_event: Optional[dict],
                    maturity_event: Optional[dict], today: date) -> List[Dict[str, str]]:
    warnings: List[Dict[str, str]] = []

    if current_cash > 0 and cash_365 < (current_cash * 0.85):
        warnings.append({"level": "warning", "key": "cash_flow_warning_decrease_significant"})

    if expense_event is not None:
        days_until_expense = (date.fromisoformat(expense_event["date"]) - today).days
        if days_until_expense <= 60 and abs(expense_event["amount"]) > max(current_cash * 0.20, 1):
            warnings.append({"level": "danger", "key": "cash_flow_warning_large_expense"})

    if maturity_event is not None:
        days_to_maturity = (date.fromisoformat(maturity_event["date"]) - today).days
        if days_to_maturity <= 45:
            warnings.append({"level": "info", "key": "cash_flow_warning_maturity_soon"})

    if not warnings:
        warnings.append({"level": "success", "key": "cash_flow_warning_healthy"})

    return warnings
