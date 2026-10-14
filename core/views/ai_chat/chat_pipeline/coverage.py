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


_MONTH_NAMES = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")


def period_in_context(context_text: str, period: str) -> bool:
    """period is 'YYYY-MM'. True when the evidence has that month as a row: numeric or named month (full or 3-letter),
    in either key order, compact or spaced JSON, or as an ISO date/month string ('2026-08', '2026-08-14')."""
    try:
        year, month = period.split("-")
        y, m = int(year), int(month)
    except (ValueError, AttributeError):
        return False
    if not 1 <= m <= 12:
        return False
    name = _MONTH_NAMES[m - 1]
    mon = rf'(?:{m}|"{m:02d}"|"{name}"|"{name[:3]}"|"{name.title()}"|"{name[:3].title()}")'
    sep = r'\s*(?:,\s*(?:"[a-z_]+"\s*:\s*(?:"[^"]*"|[-\d.]+|null|true|false)\s*,\s*){0,6})?'
    patterns = (rf'"year"\s*:\s*{y}{sep}"month"\s*:\s*{mon}\b', rf'"month"\s*:\s*{mon}{sep}"year"\s*:\s*{y}\b',
                rf'\b{y}-{m:02d}(?:-\d{{2}})?\b')
    text = context_text or ""
    return any(re.search(pat, text, re.IGNORECASE) for pat in patterns)


def periods_covered(context_text: str, periods: list[str], topics: list[str]) -> bool:
    """True only when every requested period has a month row in context AND the question is
    about expenses only (advisor:* topics ignored). Conservative: anything else -> False."""
    if not periods:
        return False
    data_topics = {t for t in (topics or []) if not t.startswith("advisor:")}
    if not data_topics or not data_topics <= _PERIOD_TOPICS:
        return False
    return all(period_in_context(context_text, p) for p in periods)
