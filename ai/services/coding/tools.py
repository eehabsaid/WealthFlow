"""Agent tools (sysadmin only, read-only): the same context picker and change-plan check the scripts use."""

from __future__ import annotations

from ai.services.coding import ROOT, context, index
from ai.services.coding.plan import plan_check


def _guard(user):
    from ai.services.investigation.code_tools import _guard as guard   # imported late: the investigator imports this module

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


def _local_only(user):
    """The change / run tools: sysadmin with code access, on the local development server only."""
    from ai.services.coding import edit

    denied = _guard(user)
    if denied:
        return denied
    return None if edit.enabled() else {"error": "Changing and running code is available only on the local development server (DEBUG on)."}


def propose_edit(user, params):
    denied = _local_only(user)
    if denied:
        return denied
    from ai.services.actions.codefile import propose_card

    return propose_card(user, {k: params.get(k) for k in ("path", "old_str", "new_str", "content")})


def run_checks(user, params):
    denied = _local_only(user)
    if denied:
        return denied
    from ai.services.coding.verify import verify

    files = [str(f).replace("\\", "/") for f in (params.get("files") or []) if str(f).strip()][:30]
    if not files:
        return {"error": "give `files`: the paths you changed"}
    result = verify(files, full_suite=bool(params.get("full_suite")), timeout=600)
    return {"overall": result["overall"], "steps": [{"step": s["step"], "status": s["status"], "detail": s["detail"][-400:]} for s in result["steps"]],
            "protected_files_changed": result["protected_files_changed"]}


def git_diff(user, params):
    import subprocess

    from ai.services.investigation import paths

    denied = _guard(user)
    if denied:
        return denied
    path = str(params.get("path") or "").strip().replace("\\", "/")
    try:
        if path:
            paths.resolve(path)
    except paths.PathError as exc:
        return {"error": str(exc)}
    cmd = ["git", "diff", "--", path] if path else ["git", "status", "--porcelain"]
    done = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    return {"output": paths.redact(done.stdout)[:6000], "truncated": len(done.stdout) > 6000}
