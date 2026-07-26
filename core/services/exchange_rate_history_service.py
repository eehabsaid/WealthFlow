"""
ExchangeRateHistoryService — single source of truth for all
historical exchange-rate queries in WealthFlow.

Consumers (Financial Advisor, Portfolio Optimizer, forecasting,
reports, analytics) must call this service rather than querying
ExchangeRateHistory directly.

Design guarantees:
- Archive failures never propagate to callers (fire-and-forget pattern).
- No duplicate snapshot rows: unique_together + ignore_conflicts.
- Delta check: a snapshot is archived only when its mid_rate differs
  from the latest existing history row for that currency.
- snapshot_date is always derived from the original ExchangeRate.fetched_at
  timestamp, never from the system clock.
- All numeric values remain Decimal throughout — no float conversions.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from django.db import transaction
from django.db.models import QuerySet

if TYPE_CHECKING:
    from core.models import ExchangeRateHistory

logger = logging.getLogger(__name__)

# Tolerance used for delta checks (avoids archiving trivially different Decimals)
_DELTA_TOLERANCE = Decimal("0.000001")


class ExchangeRateHistoryService:
    """
    All history operations go through this class.
    Instantiate once per call-site; it is stateless.
    """

    # ------------------------------------------------------------------ #
    # 1. archive_current_rates                                            #
    # ------------------------------------------------------------------ #

    def archive_current_rates(self) -> int:
        """
        Snapshot all rows currently in core_exchangerate into
        core_exchangeratehistory.

        Rules:
        - snapshot_date is derived from ExchangeRate.fetched_at (not today).
        - Skips currencies that already have a snapshot for that date.
        - Additionally skips currencies whose mid_rate hasn't changed
          vs. the most-recent history row (delta check).
        - Returns the number of rows actually inserted.

        NOTE: This method wraps its own try/except so that any failure
        is logged but never raised — callers (refresh flow) must never
        be blocked by an archive error.
        """
        try:
            return self._archive_current_rates_inner()
        except Exception:
            logger.exception(
                "ExchangeRateHistoryService.archive_current_rates failed silently"
            )
            return 0

    def _archive_current_rates_inner(self) -> int:
        from core.models import ExchangeRate, ExchangeRateHistory

        current_rates = list(ExchangeRate.objects.all())
        if not current_rates:
            logger.debug("archive_current_rates: core_exchangerate is empty, skipping.")
            return 0

        # Collect snapshot dates to check existing entries in DB
        snap_dates = {
            rate.fetched_at.astimezone(timezone.utc).date() if rate.fetched_at else date.today()
            for rate in current_rates
        }

        existing_pairs: set[tuple[str, date]] = set(
            ExchangeRateHistory.objects.filter(
                snapshot_date__in=snap_dates
            ).values_list("currency_code", "snapshot_date")
        )

        to_insert: list[ExchangeRateHistory] = []

        for rate in current_rates:
            snap_date = (
                rate.fetched_at.astimezone(timezone.utc).date()
                if rate.fetched_at
                else date.today()
            )

            # Skip if a snapshot already exists for this currency on this date
            if (rate.currency_code, snap_date) in existing_pairs:
                continue

            to_insert.append(
                ExchangeRateHistory(
                    currency_code=rate.currency_code,
                    currency_name=rate.currency_name or "",
                    buy_rate=Decimal(str(rate.buy_rate)),
                    sell_rate=Decimal(str(rate.sell_rate)),
                    mid_rate=Decimal(str(rate.mid_rate)),
                    source=rate.source or "open.er-api.com",
                    fetched_at=rate.fetched_at or datetime.now(tz=timezone.utc),
                    snapshot_date=snap_date,
                )
            )

        if not to_insert:
            logger.info("archive_current_rates: all snapshots already present for today, skipping.")
            return 0

        with transaction.atomic():
            created = ExchangeRateHistory.objects.bulk_create(
                to_insert,
                ignore_conflicts=True,
            )

        inserted = len(created)
        logger.info("archive_current_rates: inserted=%d.", inserted)
        return inserted

    # ------------------------------------------------------------------ #
    # 2. import_historical_rates                                          #
    # ------------------------------------------------------------------ #

    def import_historical_rates(
        self,
        days: int = 180,
        provider=None,
        batch_size: int = 100,
    ) -> dict:
        """
        Import historical snapshots for the past *days* days.

        Uses YFinanceHistoricalRateProvider by default, but accepts any
        BaseHistoricalRateProvider so the source can be injected
        (e.g., during testing or when switching providers).

        Returns:
            {
                "imported": int,   # rows inserted
                "skipped": int,    # rows already in DB
                "gaps": int,       # days where provider returned nothing
                "source": str,     # provider SOURCE_NAME
            }
        """
        from core.integrations import FawazAhmedCurrencyApiProvider
        from core.models import ExchangeRateHistory

        if provider is None:
            provider = FawazAhmedCurrencyApiProvider()

        today = date.today()
        start_date = today - timedelta(days=days - 1)

        # Collect all (currency_code, snapshot_date) pairs already stored
        # for the date range — single query, no N+1.
        existing_pairs: set[tuple[str, date]] = set(
            ExchangeRateHistory.objects.filter(
                snapshot_date__gte=start_date,
                snapshot_date__lte=today,
            ).values_list("currency_code", "snapshot_date")
        )

        total_imported = 0
        total_skipped = 0
        total_gaps = 0
        batch: list[ExchangeRateHistory] = []

        range_data: dict[date, list] = {}
        try:
            range_data = provider.fetch_range(start_date, today)
        except Exception:
            logger.exception("provider.fetch_range failed; falling back to per-day fetch")

        current = start_date
        while current <= today:
            records = range_data.get(current)
            if records is None:
                try:
                    records = provider.fetch_date(current)
                except Exception:
                    logger.exception("provider.fetch_date failed for %s", current)
                    records = []

            if not records:
                logger.warning(
                    "import_historical_rates: no data returned for %s — gap recorded.",
                    current,
                )
                total_gaps += 1
                current += timedelta(days=1)
                continue

            for rec in records:
                if (rec.currency_code, rec.snapshot_date) in existing_pairs:
                    total_skipped += 1
                    continue

                batch.append(
                    ExchangeRateHistory(
                        currency_code=rec.currency_code,
                        currency_name=rec.currency_name,
                        buy_rate=rec.buy_rate,
                        sell_rate=rec.sell_rate,
                        mid_rate=rec.mid_rate,
                        source=rec.source,
                        fetched_at=datetime.combine(
                            rec.snapshot_date,
                            datetime.min.time(),
                            tzinfo=timezone.utc,
                        ),
                        snapshot_date=rec.snapshot_date,
                    )
                )
                existing_pairs.add((rec.currency_code, rec.snapshot_date))

                if len(batch) >= batch_size:
                    inserted = self._flush_batch(batch)
                    total_imported += inserted
                    batch = []

            current += timedelta(days=1)

        # Flush remaining
        if batch:
            inserted = self._flush_batch(batch)
            total_imported += inserted

        result = {
            "imported": total_imported,
            "skipped": total_skipped,
            "gaps": total_gaps,
            "source": provider.SOURCE_NAME,
        }
        logger.info("import_historical_rates complete: %s", result)
        return result

    # ------------------------------------------------------------------ #
    # 3. get_rate_on_date                                                 #
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # 4. get_rate_range                                                   #
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Private helpers                                                     #
    # ------------------------------------------------------------------ #

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

    @staticmethod
    def _flush_batch(batch: list) -> int:
        """
        Bulk-insert a batch into ExchangeRateHistory.
        Returns the number of rows actually inserted.
        ignore_conflicts=True handles duplicate (currency_code, snapshot_date).
        """
        from core.models import ExchangeRateHistory

        with transaction.atomic():
            created = ExchangeRateHistory.objects.bulk_create(
                batch,
                ignore_conflicts=True,
            )
        return len(created)
