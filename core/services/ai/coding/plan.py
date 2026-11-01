"""Change plan check: for the files someone wants to change, what is protected, who calls them, which tests cover them, how long they are.
Everything is computed from the repo; nothing is guessed."""

from __future__ import annotations

from . import ROOT, index
from .config import load, protected_reason, test_module


def _module_of(path: str) -> str:
    return path.replace("\\", "/").removesuffix(".py").replace("/", ".")


def plan_check(files: list[str]) -> dict:
    limit = load()["max_file_lines"]
    idx = index.get()["files"]
    rows, tests, approvals = [], set(), []
    for raw in files:
        path = raw.replace("\\", "/").lstrip("./")
        target = ROOT / path
        exists = target.is_file()
        lines = idx.get(path, {}).get("lines") or (target.read_text(encoding="utf-8", errors="replace").count("\n") + 1 if exists else 0)
        reason = protected_reason(path)
        module = _module_of(path)
        symbols = idx.get(path, {}).get("classes", []) + idx.get(path, {}).get("functions", [])
        callers = sorted({c for c in index.callers(module.split(".")[-1]) if c != path} | {c for s in symbols[:10] for c in index.callers(s) if c != path})
        area = test_module(path)
        if area:
            tests.add(area)
        if reason:
            approvals.append(path)
        rows.append({"file": path, "exists": exists, "lines": lines, "over_limit": lines > limit, "protected": reason, "tests": area,
                     "callers": callers[:15], "caller_count": len(callers)})
    return {"files": rows, "tests_to_run": sorted(tests), "needs_owner_approval": approvals, "max_file_lines": limit,
            "note": "Files marked protected must not change without the owner's explicit approval. Callers are files that import the file's classes or functions."}
