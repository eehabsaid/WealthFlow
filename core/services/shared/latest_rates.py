"""One definition of "the current exchange rate row of each currency": newest `fetched_at`, ties broken by the higher id.

The same rule CurrencyConversionService uses (order_by "-fetched_at", "-id"). Several screens used Max("id") or
Max("fetched_at") alone, which disagreed with it when a row was back-filled or two rows shared a timestamp."""

from __future__ import annotations

from django.db.models import OuterRef, QuerySet, Subquery

from core.models import ExchangeRate


def latest_exchange_rates() -> QuerySet:
    """ExchangeRate rows: exactly one (the current one) per currency_code."""
    newest = ExchangeRate.objects.filter(currency_code=OuterRef("currency_code")).order_by("-fetched_at", "-id").values("id")[:1]
    return ExchangeRate.objects.filter(id=Subquery(newest))
