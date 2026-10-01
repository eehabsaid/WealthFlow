"""Helpers shared by executors: money formatting (identical to BaseContextProvider.format_currency),
the user's home currency, table-cell hygiene and owner-scoped provider access."""

from __future__ import annotations

from typing import Any

MAX_ROWS = 300


def money(value: float, code: str) -> str:
    return f"{float(value or 0):,.2f} {str(code or '').strip().upper()}"


def home_currency(user: Any) -> str:
    from core.services.shared.base_currency import get_user_base_code

    return get_user_base_code(user)


def cell(text: Any, limit: int = 40) -> str:
    s = " ".join(str(text or "").replace("|", "/").split())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def provider_data(key: str, user: Any) -> dict[str, Any]:
    """Run a registered provider's own owner-scoped aggregation (all rows, no cap)."""
    from core.services.ai.providers.registry import get_data_provider

    provider = get_data_provider(key)
    if provider is None:
        raise LookupError(f"provider {key!r} is not registered")
    return provider.get_data(user, limit=100000)
