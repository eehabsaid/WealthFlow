"""Registry entries for the knowledge-index investigation tools (merged into the investigator's tools in investigation/defs.py)."""

from __future__ import annotations

from typing import Any

from ai.services.investigation.defs_helpers import A as _A, B as _B, I as _I, S as _S, p as _p, tool as _tool
from ai.services.knowledge_index import tools as kt

NAMES = ("app_search", "app_symbol", "app_trace_calls", "app_trace_flow", "app_model_relations", "app_find_tests", "app_compare",
         "app_diagnose", "app_verify_fix", "app_index_status")

KNOWLEDGE_TOOL_DEFS: dict[str, dict[str, Any]] = {t["name"]: t for t in (
    _tool("app_search", "FIRST STEP for any code question. Hybrid search of the whole repo index (Python, JavaScript, templates, CSS, routes, models, "
          "docs, UI text in en/ar/fr/de): exact names, words, and meaning. Returns evidence: file, line range, symbol, the real source and its relations. "
          "Entries with stale=true are not current. If nothing matches, the thing may not exist: say so.",
          kt.search_tool, {"query": _p(_S, "identifier or question in words, e.g. 'net worth calculation' or 'NetWorthService'"),
                           "path": _p(_S, "optional folder/file prefix, e.g. core/services/balance"),
                           "kind": _p(_S, "optional comma list: function, method, class, field, route, component, variable, css_rule, i18n_key, doc_section, page_doc"),
                           "limit": _p(_I, "default 8, max 15"), "context_paths": _p(_A, "files already being looked at: nearby code ranks higher")}, ["query"]),
    _tool("app_symbol", "Exact definition lookup of a function, class, model, JS global or route: every definition with its real source (up to 60 lines), "
          "line range and relations. Use after app_search to read the chosen symbol.",
          kt.symbol_tool, {"name": _p(_S, "e.g. ExpenseService.apply_reverse or wfSyncRatePivot"), "kind": _p(_S, "optional comma list of kinds")}, ["name"]),
    _tool("app_trace_calls", "Follow execution: who calls a function (up) and what it calls (down), several levels. Matching is by NAME and says when a name "
          "is shared by several definitions. Read the returned ranges before claiming what a path does.",
          kt.trace_calls_tool, {"symbol": _p(_S, "function, method or class name"), "direction": _p(_S, "up, down or both (default both)"),
                                "depth": _p(_I, "levels, default 2, max 3")}, ["symbol"]),
    _tool("app_trace_flow", "Trace a feature from the screen to the database: template handlers -> JS functions -> '/api/...' calls -> Django routes -> views -> "
          "services -> models. Lists the gaps where a link could not be proven (dynamic URLs, etc.). Use for 'where does this screen get its data'.",
          kt.trace_flow_tool, {"target": _p(_S, "JS function name, API path fragment (e.g. cash-flow-forecast) or a feature in words")}, ["target"]),
    _tool("app_model_relations", "A Django model: all fields, foreign keys out and in, owner (multi-tenant) field, migrations touching it, where it is used, tests.",
          kt.model_tool, {"model": _p(_S, "model class name, e.g. Expense")}, ["model"]),
    _tool("app_find_tests", "Tests that reference a symbol or a source file (matched by name; not a coverage measurement).",
          kt.tests_tool, {"target": _p(_S, "symbol name or file path")}, ["target"]),
    _tool("app_compare", "Compare two related implementations (e.g. two services or two JS renderers): both sources, calls only one makes, and a diff.",
          kt.compare_tool, {"a": _p(_S, "first function/class"), "b": _p(_S, "second function/class")}, ["a", "b"]),
    _tool("app_diagnose", "Investigate an error: paste a traceback / console error / message. Maps frames to real source lines (confirmed) and lists root-cause "
          "HYPOTHESES (not confirmed) with how to verify each. Never state a hypothesis as the cause until a tool result confirms it.",
          kt.diagnose_tool, {"error": _p(_S, "traceback, console error or error message")}, ["error"]),
    _tool("app_verify_fix", "Check a proposed fix against the real code BEFORE app_propose_edit: old text still matches, patched file parses, symbols exist, "
          "callers and tests affected, protected file, 200-line rule. Static only; run app_run_checks after the change.",
          kt.verify_tool, {"path": _p(_S, "repo-relative file"), "old_text": _p(_S, "exact current text to replace"),
                           "new_text": _p(_S, "replacement text"), "uses_symbols": _p(_A, "names the new code calls or relies on")}, ["path", "old_text"]),
    _tool("app_index_status", "Health of the code index: version, state, counts, files that differ from disk. refresh=true re-checks and updates it now.",
          kt.status_tool, {"refresh": _p(_B, "re-check and update the index first")}),
)}
