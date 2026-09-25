"""
Standardized Base Context Provider interface for modular, read-only AI context extraction.
CRITICAL CONSTRAINT: 100% READ-ONLY. Subclasses MUST NEVER call .save(), .delete(), .create(), or .update().
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import logging

logger = logging.getLogger(__name__)


class BaseContextProvider(ABC):
    @property
    @abstractmethod
    def key(self) -> str:
        """Unique provider key, e.g. 'salary', 'balance', 'expenses'."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        pass

    @property
    def supported_domains(self) -> list[str]:
        """List of supported question domains (default: ['business_data_analysis'])."""
        return ["business_data_analysis"]

    @property
    def cache_ttl(self) -> float:
        """Default cache TTL in seconds (default: 600s)."""
        return 600.0

    @property
    def is_read_only(self) -> bool:
        """Strict read-only flag. Always returns True."""
        return True

    def get_capabilities(self) -> list[dict[str, Any]]:
        """Declare capabilities provided by this context provider."""
        return []

    @abstractmethod
    def get_data(self, user: Any, limit: int | None = None) -> dict[str, Any]:
        """Fetch read-only data dictionary for the given user."""
        pass

    def get_user_primary_currency(self, user: Any) -> str:
        """Resolves active user's default (primary) currency code."""
        from core.services.shared.base_currency import get_user_base_code
        return get_user_base_code(user)

    def convert_to_home_currency(self, amount: float, from_code: str, home_code: str = "") -> float:
        """
        Deterministically converts an amount from `from_code` to `home_code` using ExchangeRate model.
        Returns amount converted or float(amount) if codes match or rate unavailable.
        """
        if not amount:
            return 0.0
        val = float(amount)
        f_code = str(from_code or home_code).strip().upper()
        from core.services.shared.base_currency import platform_default_code
        h_code = str(home_code or platform_default_code()).strip().upper()

        if f_code == h_code:
            return val

        try:
            from core.models import ExchangeRate
            from core.services.shared.currency_conversion_service import get_rate_pivot_code

            def _mid(code: str) -> float:
                # ExchangeRate maps currency_code -> pivot-currency rate (mid_rate)
                if code == get_rate_pivot_code():
                    return 1.0
                row = ExchangeRate.objects.filter(currency_code__iexact=code).order_by("-fetched_at").first()
                return float((row.mid_rate or row.buy_rate or row.sell_rate or 0) if row else 0)

            from_mid, home_mid = _mid(f_code), _mid(h_code)
            if from_mid > 0 and home_mid > 0:
                return round(val * from_mid / home_mid, 2)
        except Exception as exc:
            logger.warning("Currency conversion failed for %s -> %s: %s", f_code, h_code, exc)

        return val

    def format_currency(self, amount: float, currency_code: str) -> str:
        """Formats amount with thousands separators and currency code."""
        val = float(amount or 0)
        return f"{val:,.2f} {currency_code.strip().upper()}"


BaseDataProvider = BaseContextProvider
