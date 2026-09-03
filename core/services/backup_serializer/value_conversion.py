"""
Primitive value <-> JSON-safe conversion helpers used by backup export and
restore.
"""

from __future__ import annotations

import base64
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


def serialize_value(value: Any) -> Any:
    """Convert a Python / Django field value to a JSON-safe primitive."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, memoryview)):
        raw = bytes(value) if isinstance(value, memoryview) else value
        return base64.b64encode(raw).decode("ascii")
    return value


def deserialize_date(raw: str | None) -> date | None:
    if not raw:
        return None
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(raw[:10])
    except (ValueError, TypeError):
        return None


def deserialize_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


def deserialize_decimal(raw: Any, default: str = "0.00") -> Decimal:
    if raw is None:
        return Decimal(default)
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def deserialize_binary(raw: str | None) -> bytes | None:
    if not raw:
        return None
    try:
        return base64.b64decode(raw.encode("ascii"))
    except Exception:
        return None
