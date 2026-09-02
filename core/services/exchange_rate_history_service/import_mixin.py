from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from django.db import transaction

logger = logging.getLogger(__name__)


class ImportMixin:
    """Imports historical exchange-rate snapshots from an external provider."""

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
