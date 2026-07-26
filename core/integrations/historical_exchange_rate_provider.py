"""
Historical exchange-rate provider abstraction.

The provider is encapsulated behind a base class so the underlying
data source can be replaced without touching ExchangeRateHistoryService
or any of its consumers.

Current implementation: exchangerate.host (free public API, no key required).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

logger = logging.getLogger(__name__)

# Currencies mirrored from ExchangeRateService.CURRENCY_NAMES
_SYMBOLS = [
    "USD", "EUR", "GBP", "SAR", "AED", "KWD", "CAD", "CHF",
    "JPY", "CNY", "QAR", "BHD", "OMR", "JOD", "NOK", "SEK",
    "DKK", "AUD",
]

_CURRENCY_NAMES: dict[str, str] = {
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


class ExchangeRateHostProvider(BaseHistoricalRateProvider):
    """
    Historical rates via api.exchangerate.host (free, no API key).

    Endpoint: GET https://api.exchangerate.host/historical
              ?date=YYYY-MM-DD&base=EGP&symbols=USD,EUR,...

    Retry/backoff: up to *max_retries* attempts with exponential back-off
    starting at *initial_delay* seconds.
    """

    SOURCE_NAME = "exchangerate.host"

    _BASE_URL = "https://api.exchangerate.host/historical"
    _SYMBOLS_PARAM = ",".join(_SYMBOLS)

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 2.0,
        timeout: int = 20,
        user_agent: str = "WealthFlow/1.0",
    ) -> None:
        self._max_retries = max_retries
        self._initial_delay = initial_delay
        self._timeout = timeout
        self._user_agent = user_agent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_date(self, target_date: date) -> list[HistoricalRateRecord]:
        date_str = target_date.strftime("%Y-%m-%d")
        url = (
            f"{self._BASE_URL}"
            f"?date={date_str}"
            f"&base=EGP"
            f"&symbols={self._SYMBOLS_PARAM}"
        )

        raw = self._fetch_with_retry(url, date_str)
        if raw is None:
            return []

        return self._parse(raw, target_date)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_with_retry(self, url: str, date_str: str) -> Optional[dict]:
        delay = self._initial_delay
        for attempt in range(1, self._max_retries + 1):
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": self._user_agent}
                )
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    data = json.loads(resp.read().decode())
                if data.get("success") is False:
                    logger.warning(
                        "exchangerate.host: non-success for %s (attempt %d/%d)",
                        date_str,
                        attempt,
                        self._max_retries,
                    )
                    return None
                return data
            except urllib.error.HTTPError as exc:
                logger.warning(
                    "exchangerate.host HTTP %s for %s (attempt %d/%d)",
                    exc.code,
                    date_str,
                    attempt,
                    self._max_retries,
                )
            except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "exchangerate.host error for %s (attempt %d/%d): %s",
                    date_str,
                    attempt,
                    self._max_retries,
                    exc,
                )
            if attempt < self._max_retries:
                logger.debug("Retrying in %.1f s ...", delay)
                time.sleep(delay)
                delay *= 2  # exponential back-off
        logger.error(
            "exchangerate.host: all %d attempts failed for %s — skipping day.",
            self._max_retries,
            date_str,
        )
        return None

    def _parse(self, data: dict, snapshot_date: date) -> list[HistoricalRateRecord]:
        quotes: dict = data.get("quotes", {}) or data.get("rates", {})
        records: list[HistoricalRateRecord] = []

        for code in _SYMBOLS:
            # API returns rates as EGP → currency (EGP is base → 1/rate = EGP per unit)
            raw_rate = quotes.get(f"EGP{code}") or quotes.get(code)
            if not raw_rate:
                continue
            try:
                # Keep full precision — work only in Decimal
                rate_decimal = Decimal(str(raw_rate))
                if rate_decimal == 0:
                    continue
                # EGP per one foreign unit
                egp_per_unit = Decimal("1") / rate_decimal
                spread = egp_per_unit * Decimal("0.005")
                records.append(
                    HistoricalRateRecord(
                        currency_code=code,
                        currency_name=_CURRENCY_NAMES.get(code, code),
                        buy_rate=(egp_per_unit - spread).quantize(
                            Decimal("0.000001")
                        ),
                        sell_rate=(egp_per_unit + spread).quantize(
                            Decimal("0.000001")
                        ),
                        mid_rate=egp_per_unit.quantize(Decimal("0.000001")),
                        source=self.SOURCE_NAME,
                        snapshot_date=snapshot_date,
                    )
                )
            except (InvalidOperation, ZeroDivisionError) as exc:
                logger.warning(
                    "Skipping %s for %s — parse error: %s", code, snapshot_date, exc
                )
        return records
