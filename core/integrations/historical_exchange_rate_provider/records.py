"""
Value object and abstract base for historical exchange-rate providers.

Split out of the former monolithic historical_exchange_rate_provider.py
(200-line rule).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, timedelta
from decimal import Decimal

# Currencies mirrored from ExchangeRateService.CURRENCY_NAMES
SYMBOLS: list[str] = [
    "USD", "EUR", "GBP", "SAR", "AED", "KWD", "CAD", "CHF",
    "JPY", "CNY", "QAR", "BHD", "OMR", "JOD", "NOK", "SEK",
    "DKK", "AUD",
]

CURRENCY_NAMES: dict[str, str] = {
    "USD": "US Dollar",
    "EUR": "Euro",
    "GBP": "Pound Sterling",
    "SAR": "Saudi Riyal",
    "AED": "UAE Dirham",
    "KWD": "Kuwaiti Dinar",
    "CAD": "Canadian Dollar",
    "CHF": "Swiss Franc",
    "JPY": "Japanese Yen",
    "CNY": "Chinese Yuan",
    "QAR": "Qatari Riyal",
    "BHD": "Bahraini Dinar",
    "OMR": "Omani Riyal",
    "JOD": "Jordanian Dinar",
    "NOK": "Norwegian Krone",
    "SEK": "Swedish Krona",
    "DKK": "Danish Krone",
    "AUD": "Australian Dollar",
}


class HistoricalRateRecord:
    """
    Value object returned by providers.
    All numeric fields are Decimal — never float.
    """

    __slots__ = (
        "currency_code",
        "currency_name",
        "buy_rate",
        "sell_rate",
        "mid_rate",
        "source",
        "snapshot_date",
    )

    def __init__(
        self,
        currency_code: str,
        currency_name: str,
        buy_rate: Decimal,
        sell_rate: Decimal,
        mid_rate: Decimal,
        source: str,
        snapshot_date: date,
    ) -> None:
        self.currency_code = currency_code
        self.currency_name = currency_name
        self.buy_rate = buy_rate
        self.sell_rate = sell_rate
        self.mid_rate = mid_rate
        self.source = source
        self.snapshot_date = snapshot_date


class BaseHistoricalRateProvider(ABC):
    """
    Abstract base for historical exchange-rate data sources.

    Implement fetch_date() in a subclass to support a new provider.
    ExchangeRateHistoryService depends only on this interface.
    """

    SOURCE_NAME: str = "unknown"

    @abstractmethod
    def fetch_date(self, target_date: date) -> list[HistoricalRateRecord]:
        """
        Fetch all known currency rates for *target_date*.

        Returns an empty list if no data is available.
        Must never raise — log errors and return [].
        """

    def fetch_range(
        self, start: date, end: date
    ) -> dict[date, list[HistoricalRateRecord]]:
        """
        Fetch all known currency rates for a date range [start, end].
        Default implementation calls fetch_date for each date.
        """
        result: dict[date, list[HistoricalRateRecord]] = {}
        current = start
        while current <= end:
            result[current] = self.fetch_date(current)
            current += timedelta(days=1)
        return result
