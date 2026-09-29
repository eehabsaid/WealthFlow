"""Does the retrieved context already contain the month(s) the user asked about?

LLM-free (regex over the assembled context, ~sub-ms). Used by reason.answer_from_context:
a tool round trip for a month that is already in the snapshot fetches the same provider data
again (query_application_data reads the same providers as Retrieve), so it only costs time:
tool schemas ~810 tok (~22 s prefill) + tool-call decode + result prefill.
"""

from __future__ import annotations

import re

# Topics whose month-level rows are emitted by the expenses provider (monthly_summary /
# monthly_category_breakdown carry "year":Y,"month":M). Any other topic keeps tools on.
_PERIOD_TOPICS = frozenset({"expenses"})


def period_in_context(context_text: str, period: str) -> bool:
    """period is 'YYYY-MM'. Matches compact-JSON and spaced-JSON month rows."""
    try:
        year, month = period.split("-")
        y, m = int(year), int(month)
    except (ValueError, AttributeError):
        return False
    pat = rf'"year"\s*:\s*{y}\s*,\s*"month"\s*:\s*{m}\b'
    return re.search(pat, context_text or "") is not None


def periods_covered(context_text: str, periods: list[str], topics: list[str]) -> bool:
    """True only when every requested period has a month row in context AND the question is
    about expenses only (advisor:* topics ignored). Conservative: anything else -> False."""
    if not periods:
        return False
    data_topics = {t for t in (topics or []) if not t.startswith("advisor:")}
    if not data_topics or not data_topics <= _PERIOD_TOPICS:
        return False
    return all(period_in_context(context_text, p) for p in periods)
