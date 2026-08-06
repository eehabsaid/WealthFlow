"""
Standardized Base Context Provider interface for modular, read-only AI context extraction.
CRITICAL CONSTRAINT: 100% READ-ONLY. Subclasses MUST NEVER call .save(), .delete(), .create(), or .update().
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


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
    def get_data(self, user: Any, limit: int = 20) -> dict[str, Any]:
        """Fetch read-only data dictionary for the given user."""
        pass


BaseDataProvider = BaseContextProvider
