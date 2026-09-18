"""
Historical exchange-rate provider abstraction.

The provider is encapsulated behind a base class so the underlying
data source can be replaced without touching ExchangeRateHistoryService
or any of its consumers.

Current implementation: FawazAhmedCurrencyApiProvider
  Uses Fawaz Ahmed Currency API via jsDelivr CDN.
  Free, public, open-source daily currency snapshots without API key.
  URL format: https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{YYYY-MM-DD}/v1/currencies/egp.json
  Uses standard urllib.request — zero external dependencies.

Split into a package (200-line rule):
  - records.py       : HistoricalRateRecord, BaseHistoricalRateProvider
  - fawaz_provider.py : FawazAhmedCurrencyApiProvider
  - __init__.py (this file) : umbrella re-export, preserving the exact
    import surface consumers already depend on
    (core.integrations.__init__.py, tests, etc.)
"""

from __future__ import annotations

from core.integrations.historical_exchange_rate_provider.records import (
    BaseHistoricalRateProvider,
    HistoricalRateRecord,
)
from core.integrations.historical_exchange_rate_provider.fawaz_provider import (
    FawazAhmedCurrencyApiProvider,
)

# Backward compatibility aliases
ExchangeRateHostProvider = FawazAhmedCurrencyApiProvider
YFinanceHistoricalRateProvider = FawazAhmedCurrencyApiProvider

__all__ = [
    "HistoricalRateRecord",
    "BaseHistoricalRateProvider",
    "FawazAhmedCurrencyApiProvider",
    "ExchangeRateHostProvider",
    "YFinanceHistoricalRateProvider",
]
