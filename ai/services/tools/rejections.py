"""Single builder for the (audit, result) rejection tuple returned by tool validation."""

from __future__ import annotations

from typing import Any


def make_rejection(
    tool: str, timestamp: str, params: dict[str, Any], reason: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Same audit shape every rejection path used to build inline (status "rejected", 0 ms)."""
    audit = {
        "tool": tool,
        "timestamp": timestamp,
        "status": "rejected",
        "duration_ms": 0,
        "rejection_reason": reason,
        "arguments": params,
    }
    return audit, {"ok": False, "error": reason}
