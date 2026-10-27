"""app_screen_data: the assistant's way to read what any screen of the app shows, from live data and through the screen's own
calculation. Two uses: search (find the endpoint for a screen or figure and see its query parameters) and read (call it)."""

from __future__ import annotations

from . import catalog, reader

NAME = "app_screen_data"
DESCRIPTION = (
    "Read what a SCREEN of the app shows (cash flow projection, forecasts, balances, totals, reports ...) from live data, through "
    "the screen's own calculation, for the CURRENT USER. First call it with search='<words of the screen or figure>' to find the "
    "endpoint and its query parameters; then call it with path and query (dates as YYYY-MM-DD) to get the exact numbers. Use "
    "these numbers instead of computing a figure by hand.")


def handler(user, params):
    path = str(params.get("path") or "").strip()
    if path:
        return reader.read(user, path, params.get("query"))
    return catalog.search(str(params.get("search") or ""))


PROPERTIES = {
    "search": {"type": "string", "description": "words of the screen or figure, e.g. 'cash flow projection' (empty = list the groups)"},
    "path": {"type": "string", "description": "endpoint path found by search, e.g. /api/financial-advisor/cash-flow-custom-projection/ (ids go in the path)"},
    "query": {"type": "object", "description": "the endpoint's query parameters, e.g. {\"target_date\": \"2026-11-30\"}; leave out to use the defaults"},
}
