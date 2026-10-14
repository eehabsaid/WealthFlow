"""Helpers shared by executors: money formatting (identical to BaseContextProvider.format_currency),
the user's home currency, table-cell hygiene and owner-scoped provider access."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

MAX_ROWS = 300            # rows shown in a chat table
EXPORT_ROWS = 50000       # rows written to a generated file (ai_file_max_rows still applies when the file is saved)
_EXPORT: ContextVar[int] = ContextVar("qe_export_rows", default=0)   # 0 = chat mode; N = building a file, N rows max


def row_cap() -> int:
    return _EXPORT.get() or MAX_ROWS


@contextmanager
def export_mode(rows: int = EXPORT_ROWS):
    """Executors run inside this build full tables for a file: no 300-row chat cap, no cell truncation."""
    token = _EXPORT.set(max(1, int(rows)))
    try:
        yield
    finally:
        _EXPORT.reset(token)


def money(value: float, code: str) -> str:
    return f"{float(value or 0):,.2f} {str(code or '').strip().upper()}"


def home_currency(user: Any) -> str:
    from core.services.shared.base_currency import get_user_base_code

    return get_user_base_code(user)


def cell(text: Any, limit: int = 40) -> str:
    s = " ".join(str(text or "").replace("|", "/").split())
    limit = 500 if _EXPORT.get() else limit
    return s if len(s) <= limit else s[: limit - 1] + "…"


def provider_data(key: str, user: Any) -> dict[str, Any]:
    """Run a registered provider's own owner-scoped aggregation (all rows, no cap)."""
    from core.services.ai.providers.registry import get_data_provider

    provider = get_data_provider(key)
    if provider is None:
        raise LookupError(f"provider {key!r} is not registered")
    return provider.get_data(user, limit=100000)
