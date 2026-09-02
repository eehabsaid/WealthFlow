from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.models import ExchangeRateHistory
    from django.db.models import QuerySet


class QueryMixin:
    """Read-side queries for historical exchange rates."""

    def get_rate_on_date(
        self, currency_code: str, target_date: date
    ) -> Optional["ExchangeRateHistory"]:
        """
        Return the ExchangeRateHistory row for *currency_code* on
        *target_date*, or None if no snapshot exists.

        This is the canonical lookup for all historical rate queries.
        """
        from core.models import ExchangeRateHistory

        return (
            ExchangeRateHistory.objects.filter(
                currency_code=currency_code,
                snapshot_date=target_date,
            )
            .first()
        )

    def get_rate_range(
        self,
        currency_code: str,
        start: date,
        end: date,
    ) -> "QuerySet[ExchangeRateHistory]":
        """
        Return all ExchangeRateHistory rows for *currency_code* between
        *start* and *end* (inclusive), ordered by snapshot_date ascending.

        Returns a lazy QuerySet — consumers may chain .values(), .aggregate(),
        etc. without triggering an extra query.
        """
        from core.models import ExchangeRateHistory

        return ExchangeRateHistory.objects.filter(
            currency_code=currency_code,
            snapshot_date__gte=start,
            snapshot_date__lte=end,
        ).order_by("snapshot_date")

    def _get_latest_mid_rates_from_history(
        self, currency_codes: list[str]
    ) -> dict[str, Decimal]:
        """
        Return a dict mapping currency_code → latest mid_rate from history.

        Uses a single annotated queryset — no N+1.
        """
        from django.db.models import Max

        from core.models import ExchangeRateHistory

        # Find the most-recent snapshot_date per currency in one query.
        latest_dates = (
            ExchangeRateHistory.objects.filter(
                currency_code__in=currency_codes
            )
            .values("currency_code")
            .annotate(latest_date=Max("snapshot_date"))
        )
        date_map = {
            row["currency_code"]: row["latest_date"] for row in latest_dates
        }

        if not date_map:
            return {}

        # Fetch the actual rows for those dates — still a single query.
        from django.db.models import Q

        q = Q()
        for code, snap_date in date_map.items():
            q |= Q(currency_code=code, snapshot_date=snap_date)

        rows = ExchangeRateHistory.objects.filter(q).only(
            "currency_code", "mid_rate"
        )
        return {row.currency_code: Decimal(str(row.mid_rate)) for row in rows}
