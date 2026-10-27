"""Investigator tools added for Agent mode (all read tier). Code ones are sysadmin-only via defs.CODE_TOOLS."""

from __future__ import annotations

from typing import Any

from . import app_tools as at
from . import code_extra as cx
from .defs_helpers import I as _I, S as _S, p as _p, tool as _tool
from core.services.ai.screen_data import tool as screen_tool

AGENT_TOOL_DEFS: dict[str, dict[str, Any]] = {t["name"]: t for t in (
    _tool(screen_tool.NAME, screen_tool.DESCRIPTION, screen_tool.handler, screen_tool.PROPERTIES),
    _tool("app_computed_figures",
          "Quick figures for the CURRENT USER that the chat can answer directly (net worth, balances, salary, expense totals and "
          "averages). It does NOT replace a screen: for anything a screen calculates (projections, forecasts, cash flow) use "
          "app_screen_data. Ask it as a plain question.",
          at.computed_figures, {"question": _p(_S, "e.g. 'what is my net worth' or 'average monthly expenses in 2026'")}, ["question"]),
    _tool("app_routes", "List the app's screens (route, tabs, dialogs/actions inside them); filter with a word of the screen name.",
          at.routes, {"query": _p(_S, "optional word, e.g. 'gold' or 'exchange'")}),
    _tool("app_i18n_search", "Search the app's visible UI text (labels, buttons, messages) in en/ar/fr/de; returns the text keys.",
          at.i18n_search, {"term": _p(_S, "word or UI key"), "lang": _p(_S, "en (default), ar, fr or de")}, ["term"]),
    _tool("app_callers", "Where a function, class or JS global is USED (not defined): file, line and counts per file.",
          cx.callers, {"symbol": _p(_S, "e.g. ExpenseService or wfSyncRatePivot")}, ["symbol"]),
    _tool("app_git_history", "Recent commits that touched a file (action=log) or who last changed given lines (action=blame).",
          cx.git_history, {"path": _p(_S, "file path"), "action": _p(_S, "log (default) or blame"),
                           "limit": _p(_I, "commits for log, default 8, max 15"), "start_line": _p(_I, "blame start line"),
                           "end_line": _p(_I, "blame end line (max 80 lines)")}, ["path"]),
    _tool("app_trace_feature",
          "Trace a feature through the layers: UI text -> JS -> templates -> URLs -> views -> services -> models (file:line hits per layer).",
          cx.trace_feature, {"feature": _p(_S, "feature name, e.g. 'exchange rates' or 'gold_price'")}, ["feature"]),
)}
