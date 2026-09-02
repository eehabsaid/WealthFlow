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

Sibling modules:
- archive_mixin.py  — ArchiveMixin: archive_current_rates, _archive_current_rates_inner
- import_mixin.py   — ImportMixin: import_historical_rates, _flush_batch
- query_mixin.py     — QueryMixin: get_rate_on_date, get_rate_range,
                         _get_latest_mid_rates_from_history

This file re-exports ExchangeRateHistoryService, the public entry point.
"""

from __future__ import annotations

from decimal import Decimal

from core.services.exchange_rate_history_service.archive_mixin import ArchiveMixin
from core.services.exchange_rate_history_service.import_mixin import ImportMixin
from core.services.exchange_rate_history_service.query_mixin import QueryMixin

# Tolerance used for delta checks (avoids archiving trivially different Decimals)
_DELTA_TOLERANCE = Decimal("0.000001")


class ExchangeRateHistoryService(ArchiveMixin, ImportMixin, QueryMixin):
    """
    All history operations go through this class.
    Instantiate once per call-site; it is stateless.
    """


__all__ = ["ExchangeRateHistoryService"]
