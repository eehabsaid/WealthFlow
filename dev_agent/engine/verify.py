"""Honest verification. Steps come from config.json `verify_steps` and run through the same command guard. Each result is PASSED, FAILED,
NOT RUN (with the reason) or SKIPPED (not applicable). The overall line says VERIFIED only if nothing failed and every applicable step ran."""

from __future__ import annotations

from ..guard.commands import classify
from ..tools import runner
from . import coverage, e2e

CODE_EXT = (".py", ".js", ".css", ".html")
CHUNK = 40   # keeps Windows command lines short


def _expand(argv: list[str], files: list[str], modules: list[str], pytests: list[str] | None = None) -> list[list[str]]:
    if "{pytest}" in argv:
        return [[a for t in argv for a in (pytests if t == "{pytest}" else [t])]]
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
    pytests = coverage.pytest_targets(project, changed)
    modules = sorted({m for f in changed if (m := project.test_module(f))})
    for step in project.config["verify_steps"]:
        name, exts = step["name"], tuple(step.get("ext") or ())
        files = [f for f in changed if f.endswith(exts)] if exts else changed
        if exts and not files:
            results.append({"step": name, "status": "SKIPPED", "detail": "no matching files changed"})
            continue
        if "{pytest}" in step["argv"] and not pytests:
            results.append({"step": name, "status": "SKIPPED", "detail": "no changed file belongs to a pytest area"})
            continue
        if "{modules}" in step["argv"] and not modules and pytests and not coverage.unmapped(project, changed):
            results.append({"step": name, "status": "SKIPPED", "detail": "changed files are covered by a pytest area instead"})
            continue
        if "{modules}" in step["argv"] and not modules:
            results.append({"step": name, "status": "NOT RUN", "detail": "no test module is mapped to the changed files (test_areas in config.json)"})
            continue
        outcome, detail = "PASSED", ""
        for argv in _expand(step["argv"], files, modules, pytests):
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
    if mapping := coverage.row(project, changed):
        results.append(mapping)
    results.append(_line_limits(project, changed))
    row = e2e.run(ctx, changed)
    if row:
        results.append(row)
    return results


def is_test(step: str) -> bool:
    low = step.lower()
    return ("test" in low and "mapping" not in low) or "e2e" in low


def counts(results: list[dict]) -> str:
    n = {k: sum(r["status"] == k for r in results) for k in ("PASSED", "FAILED", "SKIPPED", "NOT RUN")}
    return f"{n['PASSED']} passed, {n['FAILED']} failed, {n['SKIPPED']} skipped, {n['NOT RUN']} not run"


def tests_line(results: list[dict]) -> str:
    """Automated tests only (Django, pytest, browser E2E), each with its own status; says so when none ran."""
    tests = [r for r in results if is_test(r["step"])]
    ran = [f"{r['step']} {r['status']}" for r in tests]
    return "; ".join(ran) if ran else "no automated test step was configured for these files"


def e2e_line(results: list[dict]) -> str:
    row = next((r for r in results if r["step"] == "browser E2E"), None)
    if row is None:
        return "Browser E2E: NOT PERFORMED (no UI files changed, so it was not required)"
    why = f" - {row['detail'].splitlines()[0][:160]}" if row["detail"] else ""
    return f"Browser E2E: {row['status']}{why}" + ("" if row["status"] == "PASSED" else " - browser-level behaviour is NOT verified")


def overall(results: list[dict]) -> str:
    if any(r["status"] == "FAILED" for r in results):
        return "FAILED"
    if any(r["status"] == "NOT RUN" for r in results):
        return "NOT VERIFIED (some checks did not run)"
    if any(r["step"] != "checks" and r["status"] == "PASSED" for r in results):
        return "VERIFIED" if any(is_test(r["step"]) and r["status"] == "PASSED" for r in results) else "NOT VERIFIED (no automated test ran)"
    return "NOT VERIFIED (nothing ran)"
