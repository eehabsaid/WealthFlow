"""
FawazAhmedCurrencyApiProvider concrete implementation.

Split out of the former monolithic historical_exchange_rate_provider.py
(200-line rule).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from core.integrations.historical_exchange_rate_provider.records import (
    BaseHistoricalRateProvider,
    HistoricalRateRecord,
    CURRENCY_NAMES,
    SYMBOLS,
)

logger = logging.getLogger(__name__)


class FawazAhmedCurrencyApiProvider(BaseHistoricalRateProvider):
    """
    Historical exchange rates via Fawaz Ahmed Currency API (jsDelivr CDN).

    Endpoint: https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{YYYY-MM-DD}/v1/currencies/egp.json
    Fallback: https://raw.githubusercontent.com/fawazahmed0/currency-api/1/{YYYY-MM-DD}/currencies/egp.json
    """

    SOURCE_NAME = "fawazahmed0_cdn"

    def __init__(
        self,
        max_retries: int = 2,
        timeout: int = 8,
        user_agent: str = "WealthFlow/1.0",
    ) -> None:
        self._max_retries = max_retries
        self._timeout = timeout
        self._user_agent = user_agent

    def fetch_date(self, target_date: date) -> list[HistoricalRateRecord]:
        date_str = target_date.strftime("%Y-%m-%d")
        urls = [
            f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date_str}/v1/currencies/egp.json",
            f"https://raw.githubusercontent.com/fawazahmed0/currency-api/1/{date_str}/currencies/egp.json",
        ]

        data = None
        for url in urls:
            data = self._fetch_url(url, date_str)
            if data and "egp" in data:
                break

        if not data or "egp" not in data:
            return []

        return self._parse(data, target_date)

    def _fetch_url(self, url: str, date_str: str) -> Optional[dict]:
        for attempt in range(1, self._max_retries + 1):
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": self._user_agent}
                )
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    return None  # No data for this specific date
                logger.warning(
                    "CDN HTTP %s for %s (attempt %d/%d)", exc.code, date_str, attempt, self._max_retries
                )
            except Exception as exc:
                logger.warning(
                    "CDN fetch error for %s (attempt %d/%d): %s", date_str, attempt, self._max_retries, exc
                )
            if attempt < self._max_retries:
                time.sleep(0.5)
        return None

    def _parse(self, data: dict, snapshot_date: date) -> list[HistoricalRateRecord]:
        rates: dict = data.get("egp", {}) or {}
        records: list[HistoricalRateRecord] = []

        for code in SYMBOLS:
            raw_rate = rates.get(code.lower()) or rates.get(code)
            if not raw_rate:
                continue
            try:
                rate_dec = Decimal(str(raw_rate))
                if rate_dec <= 0:
                    continue
                egp_per_unit = Decimal("1") / rate_dec
                spread = egp_per_unit * Decimal("0.005")
                records.append(
                    HistoricalRateRecord(
                        currency_code=code,
                        currency_name=CURRENCY_NAMES.get(code, code),
                        buy_rate=(egp_per_unit - spread).quantize(Decimal("0.000001")),
                        sell_rate=(egp_per_unit + spread).quantize(Decimal("0.000001")),
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
