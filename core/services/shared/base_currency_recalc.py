"""Recalculate stored default-currency amounts when a user changes their
default currency. Original amounts and their own currencies are never
modified, so switching back restores the previous numbers.

Add an entry to RECALCULATORS for every model that stores an amount in the
default currency."""
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, List

from core.models import Expense, PerDiem
from core.services.shared.currency_conversion_service import CurrencyConversionService

CENT = Decimal("0.01")


def _rate(from_code: str, to_code: str, on_date=None) -> Decimal:
    """Rate on the entry's date when known, otherwise the latest rate."""
    try:
        return CurrencyConversionService.strict_rate(from_code, to_code, on_date)
    except ValueError:
        return CurrencyConversionService.strict_rate(from_code, to_code, None)


def _recalc_expenses(user, old_code: str, new_code: str) -> int:
    rows = list(Expense.objects.filter(owner=user).select_related("currency"))
    for row in rows:
        source = row.currency.code if row.currency_id else old_code
        row.exchange_rate = _rate(source, new_code, row.date)
        row.amount_egp = (row.amount * row.exchange_rate).quantize(CENT, rounding=ROUND_HALF_UP)
    Expense.objects.bulk_update(rows, ["exchange_rate", "amount_egp"])
    return len(rows)


def _recalc_per_diems(user, old_code: str, new_code: str) -> int:
    rows = list(PerDiem.objects.filter(company__owner=user).select_related("currency"))
    for row in rows:
        rate = _rate(row.currency.code, new_code, row.date)
        row.amount_egp = (row.amount * rate).quantize(CENT, rounding=ROUND_HALF_UP)
    PerDiem.objects.bulk_update(rows, ["amount_egp"])
    return len(rows)


RECALCULATORS: List[Callable[[object, str, str], int]] = [_recalc_expenses, _recalc_per_diems]


def recalculate_base_amounts(user, old_code: str, new_code: str) -> int:
    """Run every recalculator; raises ValueError('exchange_rate_missing') if a
    needed rate is unavailable (the caller rolls the whole change back)."""
    if str(old_code).upper() == str(new_code).upper():
        return 0
    return sum(recalculator(user, old_code, new_code) for recalculator in RECALCULATORS)
