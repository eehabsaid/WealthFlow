"""
Shared event shape and date helpers for the commitments calendar.
Kept separate from events.py / events_renewals.py to avoid a circular import.
"""
from __future__ import annotations

import calendar
from datetime import date


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _add_months(base_date: date, months: int) -> date:
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _in_range(start: date, end: date, d: date) -> bool:
    return start <= d <= end


def _shared_value(values):
    """The single non-null value every item agrees on, else None."""
    distinct = {v for v in values if v is not None}
    return distinct.pop() if len(distinct) == 1 else None


def _make(date_, category, event_type, kind, description_key, amount=0.0, amount_base=None,
         currency_code="", source="", source_id=None, status="upcoming", bank_id=None, extra=None):
    return {
        "date": date_.isoformat(),
        "category": category,
        "event_type": event_type,
        "kind": kind,
        "description_key": description_key,
        "amount": round(_to_float(amount), 2),
        "amount_base": round(_to_float(amount_base), 2) if amount_base is not None else None,
        "currency_code": currency_code,
        "source": source,
        "source_id": source_id,
        "status": status,
        "bank_id": bank_id,
        "extra": extra or {},
    }
