"""
Month-name lookup, AI-facing row cap, and chronological sort key for the
salary data provider.
"""

from __future__ import annotations

from core.models import SalaryEntry

# Caps how many entries are included in the AI-facing 'recent_monthly_timeline' list
# when the caller does not pass an explicit `limit`. Aggregates (summary, yearly_summary,
# company_breakdown) are always computed over the FULL queryset regardless of this cap —
# only the per-row timeline list is capped, to keep the JSON payload small enough to
# reliably fit in the model's context window without truncation.
MAX_TIMELINE_ENTRIES_FOR_AI = 20

MONTH_NAME_TO_INT = {
    "january": 1, "jan": 1, "1": 1, "01": 1,
    "february": 2, "feb": 2, "2": 2, "02": 2,
    "march": 3, "mar": 3, "3": 3, "03": 3,
    "april": 4, "apr": 4, "4": 4, "04": 4,
    "may": 5, "5": 5, "05": 5,
    "june": 6, "jun": 6, "6": 6, "06": 6,
    "july": 7, "jul": 7, "7": 7, "07": 7,
    "august": 8, "aug": 8, "8": 8, "08": 8,
    "september": 9, "sep": 9, "sept": 9, "9": 9, "09": 9,
    "october": 10, "oct": 10, "10": 10,
    "november": 11, "nov": 11, "11": 11,
    "december": 12, "dec": 12, "12": 12,
}


def month_sort_key(entry: SalaryEntry) -> tuple[int, int]:
    m_val = str(entry.month or "").strip().lower()
    m_idx = MONTH_NAME_TO_INT.get(m_val, 99)
    return (entry.year, m_idx)
