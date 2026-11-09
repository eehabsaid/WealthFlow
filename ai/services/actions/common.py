"""Shared pieces of the AI actions: money/date cleaning and the error type that carries a message back to the model."""

from __future__ import annotations

import datetime
from decimal import Decimal, InvalidOperation

MAX_AMOUNT = Decimal("1000000000000")


class ActionError(Exception):
    """A proposal that cannot be built. The text goes back to the model so it can ask the user instead of guessing."""


def money(value, field: str = "amount") -> Decimal:
    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise ActionError(f"`{field}` must be a number") from None
    if not amount.is_finite() or amount <= 0 or amount >= MAX_AMOUNT:
        raise ActionError(f"`{field}` must be a positive number")
    return amount.quantize(Decimal("0.01"))


def iso_date(value, field: str = "date") -> str:
    try:
        return datetime.date.fromisoformat(str(value).strip()[:10]).isoformat()
    except ValueError:
        raise ActionError(f"`{field}` must be a date written YYYY-MM-DD") from None


def pick_by_name(queryset, wanted, label: str):
    """The one row whose `name` equals `wanted` (any case). Unknown names list the valid ones so the model can ask."""
    name = " ".join(str(wanted or "").split())
    hit = queryset.filter(name__iexact=name).first()
    if hit is None:
        options = ", ".join(queryset.values_list("name", flat=True)[:30]) or "none yet"
        raise ActionError(f"no {label} named '{name}'. The user's {label}s: {options}")
    return hit


def one_of(matches: list, what: str):
    """Exactly one record, or an error that lists the candidates (the model must then ask which one)."""
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ActionError(f"no {what} matches; ask the user for more detail (date, amount, description)")
    shown = "; ".join(m["label"] for m in matches[:5])
    raise ActionError(f"{len(matches)} {what}s match, ask the user which one (pass its id as target.id): {shown}")


def changed_rows(before: dict, after: dict) -> list[dict]:
    return [{"label": k, "before": str(before.get(k, "")), "after": str(v)} for k, v in after.items() if str(before.get(k, "")) != str(v)]
