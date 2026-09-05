"""
Shared payload -> Markdown formatting for AI system context blocks.
"""

from __future__ import annotations

import json
from typing import Any

# Keys that hold raw item lists / timelines rather than summary metrics —
# split out so they can be degraded independently under token budget pressure.
_DETAIL_KEYS = {"items", "recent_monthly_timeline", "recent_expenses"}


def summarize_payload(service_key: str, payload: dict[str, Any]) -> str:
    """Formats a service/provider payload into compact, readable Markdown for AI context."""
    if not payload:
        return f"### {service_key.replace('_', ' ').title()}\nNo data available.\n"

    lines = [f"### {service_key.replace('_', ' ').title()} Payload Data:"]
    try:
        compact_json = json.dumps(payload, default=str, ensure_ascii=False, indent=2)
        lines.append(compact_json)
    except Exception:
        lines.append(str(payload))

    return "\n".join(lines) + "\n"


def split_payload_blocks(key: str, payload: Any, summarize=summarize_payload) -> tuple[list[str], list[str]]:
    """
    Splits a payload into (high_priority_blocks, low_priority_blocks) Markdown blocks,
    separating summary metrics from raw item/timeline lists so the latter can be
    degraded first if the token budget is tight.
    """
    high: list[str] = []
    low: list[str] = []

    if isinstance(payload, dict):
        summary_part = {k: v for k, v in payload.items() if k not in _DETAIL_KEYS}
        detail_part = {k: v for k, v in payload.items() if k in _DETAIL_KEYS}
        if summary_part:
            high.append(summarize(f"{key}_summary", summary_part))
        if detail_part:
            low.append(summarize(f"{key}_details", detail_part))
    else:
        high.append(summarize(key, payload))

    return high, low
