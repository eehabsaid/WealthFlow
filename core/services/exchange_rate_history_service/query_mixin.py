from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, NamedTuple, Optional

if TYPE_CHECKING:
    from core.models import ExchangeRateHistory
    from django.db.models import QuerySet


class RebasedRate(NamedTuple):
    """One historical rate expressed in a caller-chosen base currency.

    Mirrors the two ExchangeRateHistory attributes analytics code reads
    (snapshot_date, mid_rate) so it can replace a raw row one-for-one.
    """

    snapshot_date: date
    mid_rate: Decimal


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

    def get_rate_series_in_base(
        self,
        currency_code: str,
        base_code: str,
        start: date,
        end: date,
    ) -> tuple[list[RebasedRate], int]:
        """
        Return ``(series, skipped_days)``: the history of *currency_code*
        between *start* and *end* expressed in *base_code* instead of the
        platform rate pivot the archive is stored against.

        For every snapshot day: ``rate = mid(currency) / mid(base)``, both
        taken from that same day, so the result never mixes two days'
        rates. The pivot itself has no archive row (it is 1 by definition)
        and is handled as 1 on either side. A day on which the base
        currency has no archived rate cannot be converted honestly, so it
        is skipped and counted in *skipped_days* rather than guessed.

        When *base_code* is the pivot the values equal the raw mid_rate
        (quantised to the archive's own 6 decimals), so pivot-base users
        see exactly what they saw before this method existed.

        Purely additive: get_rate_range / get_rate_on_date are untouched.
        """
        from core.services.shared.currency_conversion_service import (
            get_rate_pivot_code,
        )

        code = str(currency_code or "").strip().upper()
        base = str(base_code or "").strip().upper()
        pivot = get_rate_pivot_code()
        six = Decimal("0.000001")

        num = {
            r.snapshot_date: Decimal(str(r.mid_rate))
            for r in self.get_rate_range(code, start, end)
        }
        den = {
            r.snapshot_date: Decimal(str(r.mid_rate))
            for r in self.get_rate_range(base, start, end)
        }

        if code == base:
            days = sorted(num or den)
            return [RebasedRate(d, Decimal("1").quantize(six)) for d in days], 0

        if code == pivot and not num:
            days = sorted(den)
            num = {d: Decimal("1") for d in days}
        elif base == pivot and not den:
            days = sorted(num)
            den = {d: Decimal("1") for d in days}
        else:
            days = sorted(num)

        series: list[RebasedRate] = []
        skipped = 0
        for d in days:
            n, b = num.get(d), den.get(d)
            if not n or not b or n <= 0 or b <= 0:
                skipped += 1
                continue
            series.append(RebasedRate(d, (n / b).quantize(six, rounding=ROUND_HALF_UP)))
        return series, skipped
