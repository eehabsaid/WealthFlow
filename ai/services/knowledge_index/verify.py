"""Verify a proposed fix against the CURRENT implementation, without changing anything.

Checks: the old text really exists where claimed, the patched file still parses, every symbol the fix relies on exists, who calls
the changed code, which tests reference it, protected-file status and the 200-line rule. Verdict is PASS only if no check FAILED.
"""

from __future__ import annotations

import ast

from ai.services.investigation import paths
from ai.services.knowledge_index import config, relations
from ai.services.knowledge_index.parsers import js_scan


def _check(name: str, status: str, detail: str) -> dict:
    return {"check": name, "status": status, "detail": detail}


def _balanced(text: str) -> bool:
    clean = js_scan.blank(text)
    return all(clean.count(a) == clean.count(b) for a, b in ("{}", "()", "[]"))


def verify_fix(conn, path: str, old_text: str, new_text: str | None = None, uses_symbols=None) -> dict:
    from ai.services.coding.config import load, protected_reason

    checks = []
    target = config.base_dir() / path
    source = paths.read_text(target) if target.is_file() else None
    if source is None:
        return {"verdict": "FAIL", "checks": [_check("file exists", "FAIL", f"{path} is not a readable source file")]}
    source, old_text = source.replace("\r\n", "\n"), old_text.replace("\r\n", "\n")   # Windows checkouts use CRLF; the model sends LF
    new_text = None if new_text is None else new_text.replace("\r\n", "\n")
    count = source.count(old_text) if old_text else 0
    start = source.find(old_text) if count == 1 else -1
    line = source[:start].count("\n") + 1 if start >= 0 else None
    checks.append(_check("old text matches the current file", "PASS" if count == 1 else "FAIL",
                         f"found once at line {line}" if count == 1 else f"found {count} times; copy the exact current text (app_read_file) and make it unique"))
    patched = source.replace(old_text, new_text, 1) if count == 1 and new_text is not None else None
    if patched is not None:
        if path.endswith(".py"):
            try:
                ast.parse(patched)
                checks.append(_check("patched file parses", "PASS", "Python syntax OK"))
            except SyntaxError as exc:
                checks.append(_check("patched file parses", "FAIL", f"line {exc.lineno}: {exc.msg}"))
        elif path.endswith(".js"):
            checks.append(_check("patched file brackets balance", "PASS" if _balanced(patched) else "FAIL", "(), [] and {} counts after the change"))
        limit = load()["max_file_lines"]
        n = patched.count("\n") + 1
        checks.append(_check("200-line file rule", "PASS" if n <= limit or n <= source.count("\n") + 1 else "FAIL", f"{n} lines after the change (limit {limit})"))
    for name in uses_symbols or []:
        defs = relations.definitions(conn, str(name))
        checks.append(_check(f"symbol exists: {name}", "PASS" if defs else "FAIL",
                             f"defined in {defs[0]['path']}:{defs[0]['line']}" + (f" (+{len(defs) - 1} more)" if len(defs) > 1 else "") if defs
                             else "no such function/class/variable in the index: do not use it"))
    enclosing = conn.execute("SELECT qname, name FROM symbols WHERE path=? AND kind IN ('function','method','class') AND line<=? AND end_line>=? "
                             "ORDER BY end_line-line LIMIT 1", (path, line or 0, line or 0)).fetchone() if line else None
    impact = {}
    if enclosing:
        callers = relations.callers(conn, enclosing["name"], 40)
        impact = {"changed_symbol": enclosing["qname"], "caller_count": len(callers), "caller_files": sorted({c["path"] for c in callers})[:12]}
        tests = relations.find_tests(conn, path, 8)
        impact["tests_referencing_file"] = [t["path"] for t in tests["tests"]]
        checks.append(_check("tests reference the changed code", "PASS" if tests["covered"] else "WARN",
                             f"{tests['test_files']} test file(s) mention it" if tests["covered"] else "no test mentions this file: add one"))
    reason = protected_reason(path)
    checks.append(_check("protected file", "WARN" if reason else "PASS", f"needs the owner's explicit approval: {reason}" if reason else "not protected"))
    verdict = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"
    return {"verdict": verdict, "path": path, "checks": checks, "impact": impact,
            "note": "Static verification only. It does not run tests: use app_run_checks after the change is confirmed, and report its result."}
