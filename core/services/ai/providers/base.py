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
        """Resolves active user's primary/preferred currency code."""
        from core.models import AppSettings
        if user and hasattr(user, "profile") and getattr(user.profile, "preferred_currency", None):
            pref_curr = getattr(user.profile, "preferred_currency")
            if hasattr(pref_curr, "code"):
                return str(pref_curr.code).strip().upper()
            elif pref_curr:
                return str(pref_curr).strip().upper()
        return AppSettings.get("home_currency", "EGP").strip().upper()

    def convert_to_home_currency(self, amount: float, from_code: str, home_code: str = "EGP") -> float:
        """
        Deterministically converts an amount from `from_code` to `home_code` using ExchangeRate model.
        Returns amount converted or float(amount) if codes match or rate unavailable.
        """
        if not amount:
            return 0.0
        val = float(amount)
        f_code = str(from_code or home_code).strip().upper()
        h_code = str(home_code or "EGP").strip().upper()

        if f_code == h_code:
            return val

        try:
            from core.models import ExchangeRate
            # ExchangeRate maps currency_code -> EGP rate (mid_rate)
            rate_obj = ExchangeRate.objects.filter(
                currency_code__iexact=f_code
            ).order_by("-fetched_at").first()

            if rate_obj:
                rate_val = float(rate_obj.mid_rate or rate_obj.buy_rate or rate_obj.sell_rate or 0)
                if rate_val > 0:
                    return round(val * rate_val, 2)
        except Exception as exc:
            logger.warning("Currency conversion failed for %s -> %s: %s", f_code, h_code, exc)

        return val

    def format_currency(self, amount: float, currency_code: str) -> str:
        """Formats amount with thousands separators and currency code."""
        val = float(amount or 0)
        return f"{val:,.2f} {currency_code.strip().upper()}"


BaseDataProvider = BaseContextProvider
