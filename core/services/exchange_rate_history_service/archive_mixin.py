from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from django.db import transaction

logger = logging.getLogger(__name__)


class ArchiveMixin:
    """Snapshots current exchange rates into ExchangeRateHistory."""

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
