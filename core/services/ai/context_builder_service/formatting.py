"""
Shared payload -> Markdown formatting for AI system context blocks.
"""

from __future__ import annotations

import json
from typing import Any

# Keys that hold raw item lists / timelines rather than summary metrics —
# split out so they can be degraded independently under token budget pressure.
_DETAIL_KEYS = {"items", "recent_monthly_timeline", "recent_expenses"}

# HIGH-priority keys that can still hold a large, growing-with-account-age
# array (one entry per month/year of history, one per category, etc.), kept
# in their OWN block separate from the rest of the high-priority summary.
# Without this split, one oversized key here (e.g. a long-history
# monthly_summary) shares a single combined JSON block with small
# always-important scalars (like a single last_expense field) — if the
# combined block doesn't fit the budget it's dropped as one unit, silently
# losing the small scalars too. Splitting lets the large block alone be
# dropped under pressure while the small scalar block still gets through.
_LARGE_SUMMARY_KEYS = {"monthly_summary", "yearly_summary", "category_breakdown"}


def summarize_payload(service_key: str, payload: dict[str, Any]) -> str:
    """Formats a service/provider payload into compact, readable Markdown for AI context."""
    if not payload:
        return f"### {service_key.replace('_', ' ').title()}\nNo data available.\n"

    lines = [f"### {service_key.replace('_', ' ').title()} Payload Data:"]
    try:
        # Compact (no indent) — pretty-printing wastes tokens on whitespace/
        # newlines the model doesn't need to parse a JSON block it's just quoting.
        compact_json = json.dumps(payload, default=str, ensure_ascii=False, separators=(",", ":"))
        lines.append(compact_json)
    except Exception:
        lines.append(str(payload))

    return "\n".join(lines) + "\n"


def split_payload_blocks(key: str, payload: Any, summarize=summarize_payload) -> tuple[list[str], list[str]]:
    """
    Splits a payload into (high_priority_blocks, low_priority_blocks) Markdown blocks,
    separating summary metrics from raw item/timeline lists so the latter can be
    degraded first if the token budget is tight. Within high priority, large
    growing-with-history arrays (_LARGE_SUMMARY_KEYS) get their own block, emitted
    AFTER the small scalar summary block, so a budget cut drops the large block
    first without also losing the small one (see _LARGE_SUMMARY_KEYS above).
    """
    high: list[str] = []
    low: list[str] = []

    if isinstance(payload, dict):
        detail_part = {k: v for k, v in payload.items() if k in _DETAIL_KEYS}
        large_part = {k: v for k, v in payload.items() if k in _LARGE_SUMMARY_KEYS}
        summary_part = {
            k: v for k, v in payload.items()
            if k not in _DETAIL_KEYS and k not in _LARGE_SUMMARY_KEYS
        }
        if summary_part:
            high.append(summarize(f"{key}_summary", summary_part))
        if large_part:
            high.append(summarize(f"{key}_summary_detail", large_part))
        if detail_part:
            low.append(summarize(f"{key}_details", detail_part))
    else:
        high.append(summarize(key, payload))

    return high, low
