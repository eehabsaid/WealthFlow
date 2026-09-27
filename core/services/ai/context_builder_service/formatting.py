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
# array (one entry per month/year of history, one per category, etc.), each
# kept in its OWN block, separate from the small scalar summary block AND
# from each other. Without this split, one oversized key here (e.g. a
# long-history monthly_summary) shares a combined JSON block with small
# always-important scalars (like last_expense) or with OTHER large keys —
# either way, if the combined block doesn't fit the budget, the whole thing
# is dropped as one unit, silently losing fields that would have fit fine on
# their own. Confirmed in production: category_breakdown + monthly_summary +
# monthly_category_breakdown combined (~5.1KB) didn't fit the remaining
# budget for a real account, dropping monthly_category_breakdown too even
# though it alone (~3.2KB) would have fit easily.
#
# Order matters: within one provider's large keys, they're emitted in this
# priority order (unlisted keys follow, alphabetically) so the most
# specific/directly-answering field survives a partial cut before a more
# general/redundant one does — e.g. a per-month breakdown before an all-time
# one, since the all-time one explicitly tells the model not to use it for a
# month-scoped question anyway (see category_breakdown_note).
_LARGE_SUMMARY_KEY_ORDER = ("monthly_category_breakdown", "monthly_summary", "yearly_summary", "category_breakdown")
_LARGE_SUMMARY_KEYS = set(_LARGE_SUMMARY_KEY_ORDER)


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
    degraded first if the token budget is tight. Within high priority, each large
    growing-with-history key (_LARGE_SUMMARY_KEYS) gets its OWN block, emitted AFTER
    the small scalar summary block and in _LARGE_SUMMARY_KEY_ORDER, so a budget cut
    drops the least useful/most redundant large field(s) first, one at a time,
    instead of all-or-nothing.
    """
    high: list[str] = []
    low: list[str] = []

    if isinstance(payload, dict):
        detail_part = {k: v for k, v in payload.items() if k in _DETAIL_KEYS}
        summary_part = {
            k: v for k, v in payload.items()
            if k not in _DETAIL_KEYS and k not in _LARGE_SUMMARY_KEYS
        }
        if summary_part:
            high.append(summarize(f"{key}_summary", summary_part))

        present_large_keys = [k for k in payload if k in _LARGE_SUMMARY_KEYS]
        ordered_large_keys = [k for k in _LARGE_SUMMARY_KEY_ORDER if k in present_large_keys]
        ordered_large_keys += sorted(k for k in present_large_keys if k not in _LARGE_SUMMARY_KEY_ORDER)
        for large_key in ordered_large_keys:
            high.append(summarize(f"{key}_{large_key}", {large_key: payload[large_key]}))

        if detail_part:
            low.append(summarize(f"{key}_details", detail_part))
    else:
        high.append(summarize(key, payload))

    return high, low
