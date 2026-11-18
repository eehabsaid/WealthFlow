"""Investigator tool handlers backed by the knowledge index. All sysadmin-only (same guard as the other source-code tools):
the index holds SOURCE only, never a user's financial rows, so there is nothing tenant-specific in it to leak."""

from __future__ import annotations

from ai.services.investigation import code_tools as ct
from ai.services.knowledge_index import diagnose, evidence, flow, indexer, relations, search, session, verify


def _run(user, fn, force: bool = False):
    denied = ct._guard(user)
    if denied:
        return denied
    conn, info = session.open_fresh(force=force)
    try:
        out = fn(conn)
    except Exception as exc:   # noqa: BLE001 - tools report problems to the model instead of crashing the turn
        return {"error": f"{type(exc).__name__}: {str(exc)[:200]}", "hint": "use app_grep / app_read_file as a fallback"}
    finally:
        conn.close()
    if isinstance(out, dict):
        if info["error"]:
            out["index_warning"] = (f"the index could not be refreshed ({info['error']}); results marked stale=true are NOT current. "
                                    "Confirm important facts with app_read_file.")
        elif info["refreshed"]:
            out["index_refreshed"] = info["refreshed"]
    return out


def _str(params, key: str) -> str:
    return str(params.get(key) or "").strip()


def search_tool(user, params):
    query = _str(params, "query")
    if not query:
        return {"error": "query is required: a function, class, model, screen or feature name, or a question in words"}
    kinds = tuple(k.strip() for k in _str(params, "kind").split(",") if k.strip()) or None
    ctx = tuple(p for p in params.get("context_paths") or [] if isinstance(p, str))
    limit = ct._int(params.get("limit"), 8, 1, 15)
    return _run(user, lambda c: search.search(c, query, path=_str(params, "path") or None, kinds=kinds, limit=limit, context_paths=ctx))


def symbol_tool(user, params):
    name = _str(params, "name")
    if not name:
        return {"error": "name is required, e.g. NetWorthService, apply_reverse or wfSyncRatePivot"}

    def go(conn):
        kinds = tuple(k.strip() for k in _str(params, "kind").split(",") if k.strip()) or relations.DEF_KINDS
        rows = relations.definitions(conn, name, kinds)
        if not rows:
            return {"symbol": name, "found": False, "note": "not defined anywhere in the index. Do NOT assume it exists; try app_search with words."}
        return {"symbol": name, "found": True, "definitions": [evidence.build(conn, r, max_lines=60) for r in rows[:3]],
                "more_definitions": [relations.lite(r) for r in rows[3:8]] or None}
    return _run(user, go)


def trace_calls_tool(user, params):
    name = _str(params, "symbol")
    direction = _str(params, "direction") or "both"
    if not name or direction not in ("up", "down", "both"):
        return {"error": "symbol is required; direction is up (callers), down (callees) or both"}
    return _run(user, lambda c: relations.trace_calls(c, name, direction, ct._int(params.get("depth"), 2, 1, 3)))


def trace_flow_tool(user, params):
    target = _str(params, "target")
    return _run(user, lambda c: flow.trace_flow(c, target)) if target else {"error": "target is required: a JS function, an API path or a feature name"}


def model_tool(user, params):
    model = _str(params, "model")
    return _run(user, lambda c: relations.model_relations(c, model)) if model else {"error": "model is required, e.g. Expense"}


def tests_tool(user, params):
    target = _str(params, "target")
    return _run(user, lambda c: relations.find_tests(c, target)) if target else {"error": "target is required: a symbol name or a source file path"}


def compare_tool(user, params):
    a, b = _str(params, "a"), _str(params, "b")
    return _run(user, lambda c: flow.compare(c, a, b)) if a and b else {"error": "both a and b are required (two function or class names)"}


def diagnose_tool(user, params):
    text = _str(params, "error")
    return _run(user, lambda c: diagnose.diagnose(c, text)) if text else {"error": "error is required: paste the traceback, console error or message"}


def verify_tool(user, params):
    path, old = _str(params, "path"), str(params.get("old_text") or "")
    if not path or not old:
        return {"error": "path and old_text are required (old_text = the exact current text the fix would replace)"}
    new = params.get("new_text")
    return _run(user, lambda c: verify.verify_fix(c, path, old, None if new is None else str(new), params.get("uses_symbols")))


def status_tool(user, params):
    refresh = str(params.get("refresh", "")).lower() in ("true", "1", "yes")
    return _run(user, lambda c: indexer.status(c), force=refresh)
