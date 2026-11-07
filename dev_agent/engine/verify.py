"""Honest verification. Steps come from config.json `verify_steps` and run through the same command guard. Each result is PASSED, FAILED,
NOT RUN (with the reason) or SKIPPED (not applicable). The overall line says VERIFIED only if nothing failed and every applicable step ran."""

from __future__ import annotations

import fnmatch

from ..guard.commands import classify
from ..tools import runner

CODE_EXT = (".py", ".js", ".css", ".html")
CHUNK = 40   # keeps Windows command lines short


def _expand(argv: list[str], files: list[str], modules: list[str]) -> list[list[str]]:
    if "{files}" in argv:
        return [[a for t in argv for a in (files[i:i + CHUNK] if t == "{files}" else [t])] for i in range(0, len(files), CHUNK)]
    return [[a for t in argv for a in (modules if t == "{modules}" else [t])]]


def _line_limits(project, files: list[str]) -> dict:
    limit = project.config["max_file_lines"]
    over = []
    for rel in files:
        if limit > 0 and rel.endswith(CODE_EXT):
            try:
                n = (project.root / rel).read_bytes().count(b"\n") + 1
            except OSError:
                continue
            if n > limit:
                over.append(f"{rel} ({n} lines)")
    return {"step": f"line limit ({limit})", "status": "FAILED" if over else "PASSED", "detail": "; ".join(over)}


def run(ctx, changed: list[str]) -> list[dict]:
    project, results = ctx.project, []
    if not changed:
        return [{"step": "checks", "status": "SKIPPED", "detail": "no files were written"}]
    modules = sorted({m for f in changed if (m := project.test_module(f))})
    for step in project.config["verify_steps"]:
        name, exts = step["name"], tuple(step.get("ext") or ())
        files = [f for f in changed if f.endswith(exts)] if exts else changed
        if exts and not files:
            results.append({"step": name, "status": "SKIPPED", "detail": "no matching files changed"})
            continue
        if "{modules}" in step["argv"] and not modules:
            results.append({"step": name, "status": "NOT RUN", "detail": "no test module is mapped to the changed files (test_areas in config.json)"})
            continue
        outcome, detail = "PASSED", ""
        for argv in _expand(step["argv"], files, modules):
            decision = classify(argv, project.root, project.config["commands"])
            if decision.action != "allow":
                outcome, detail = "NOT RUN", f"command is not whitelisted: {decision.reason}"
                break
            res = runner.run(argv, project.root, ctx.settings["command_timeout_s"], ctx.settings["max_tool_result_chars"], cancel=ctx.cancel)
            if res["status"] in ("NOT RUN", "CANCELLED"):
                outcome, detail = "NOT RUN", res["output"] if res["status"] == "NOT RUN" else "stopped by user"
                break
            if res["status"] == "FAILED":
                outcome, detail = "FAILED", ("TIMED OUT\n" if res["timed_out"] else "") + res["output"]
                break
        results.append({"step": name, "status": outcome, "detail": detail})
    results.append(_line_limits(project, changed))
    e2e = project.config["e2e"]
    if any(fnmatch.fnmatchcase(f.lower(), p.lower()) for f in changed for p in e2e["paths"]):
        results.append({"step": "browser E2E", "status": "NOT RUN", "detail": f"UI files changed: you must run it locally ({e2e['command'] or 'scripts/run_full_e2e.py'}); M3 adds the runner"})
    return results


def overall(results: list[dict]) -> str:
    if any(r["status"] == "FAILED" for r in results):
        return "FAILED"
    if any(r["status"] == "NOT RUN" for r in results):
        return "NOT VERIFIED (some checks did not run)"
    return "VERIFIED" if any(r["status"] == "PASSED" for r in results) else "NOT VERIFIED (nothing ran)"
