"""Agent tools (sysadmin only, read-only): the same context picker and change-plan check the scripts use."""

from __future__ import annotations

from . import context, index
from .plan import plan_check


def _guard(user):
    from core.services.ai.investigation.code_tools import _guard as guard   # imported late: the investigator imports this module

    return guard(user)


def coding_context(user, params):
    denied = _guard(user)
    if denied:
        return denied
    task = str(params.get("task") or "").strip()
    if not task:
        return {"error": "give the `task` in a sentence"}
    try:
        budget = max(1500, min(12000, int(params.get("max_chars") or 6000)))
    except (TypeError, ValueError):
        budget = 6000
    return context.pick(task, budget)


def plan_files(user, params):
    denied = _guard(user)
    if denied:
        return denied
    files = [str(f) for f in (params.get("files") or []) if str(f).strip()][:30]
    if not files:
        return {"error": "give `files`: the paths you intend to change"}
    return plan_check(files)


def repo_index(user, params):
    denied = _guard(user)
    if denied:
        return denied
    query = str(params.get("query") or "").strip()
    if not query:
        return {"error": "give a `query`: part of a file, class, function, model or route name"}
    return {"matches": index.find(query), "callers": index.callers(query) if params.get("callers") else None}
