"""Browser E2E (scripts/run_full_e2e.py) as a verification step. Mandatory when UI files changed (config.json `e2e.paths`). It runs once, in the
final checks, because it can take hours; the owner approved it in advance, so it needs no per-run question (the command comes from config.json
only, never from the model, and the deny rules still apply). If it cannot run, the step is NOT RUN with the exact reason and the report says so."""

from __future__ import annotations

import fnmatch
import importlib.util
import re

from ..guard.commands import CommandError, classify, split_command
from ..tools import runner

DEFAULT_COMMAND = "python scripts/run_full_e2e.py"
DEFAULT_TIMEOUT_S = 7200
# output that means "this machine cannot run the browser suite" (not "the change broke the app"): never sent to the model as something to fix
ENVIRONMENT = re.compile(r"playwright install|Executable doesn't exist|No module named ['\"]?playwright|executable not found|could not start:", re.I)


def ui_changed(project, changed: list[str]) -> bool:
    patterns = project.config["e2e"]["paths"]
    return any(fnmatch.fnmatchcase(f.lower(), p.lower()) for f in changed for p in patterns)


def command(project) -> list[str]:
    argv = split_command(project.config["e2e"].get("command") or DEFAULT_COMMAND)
    if argv and argv[0].lower().endswith(".py"):
        argv = ["python", *argv]   # "scripts/run_full_e2e.py" alone means: run it with the agent's interpreter
    return argv + [str(a) for a in project.config["e2e"].get("args", [])]


def playwright_available() -> bool:
    return importlib.util.find_spec("playwright") is not None


def _skip(detail: str, status: str = "NOT RUN") -> dict:
    return {"step": "browser E2E", "status": status, "detail": detail}


def run(ctx, changed: list[str]) -> dict | None:
    """One result row, or None when no UI file changed. Never raises: anything that stops it from running becomes NOT RUN with the reason."""
    project = ctx.project
    if not ui_changed(project, changed):
        return None
    if ctx.package != "final":
        return _skip("runs once, in the final checks, because it can take hours", "SKIPPED")
    try:
        argv = command(project)
    except CommandError as exc:
        return _skip(f"the e2e command in config.json cannot be read: {exc}")
    script = next((a for a in argv[1:] if a.lower().endswith(".py")), "")
    if script and not (project.root / script).is_file():
        return _skip(f"the E2E script {script} does not exist in this project; run it yourself or fix e2e.command in config.json")
    if not playwright_available():
        return _skip("Playwright is not installed for the agent's Python (pip install playwright; python -m playwright install chromium); run it yourself")
    decision = classify(argv, project.root, project.config["commands"])
    if decision.action == "deny":
        return _skip(f"command is blocked: {decision.reason}")
    ctx.emit({"type": "phase", "phase": "browser E2E (can take a long time; Stop cancels it)"})
    res = runner.run(argv, project.root, int(project.config["e2e"].get("timeout_s", DEFAULT_TIMEOUT_S)), 12000, cancel=ctx.cancel)
    if res["status"] == "CANCELLED":
        return _skip("stopped by user")
    if res["status"] == "NOT RUN" or (res["status"] == "FAILED" and ENVIRONMENT.search(res["output"])):
        return _skip(f"the browser suite could not run on this machine: {res['output'].strip()[-600:]}")
    detail = ("TIMED OUT after %ss\n" % project.config["e2e"].get("timeout_s", DEFAULT_TIMEOUT_S) if res["timed_out"] else "") + (res["output"] if res["status"] == "FAILED" else "")
    return {"step": "browser E2E", "status": res["status"], "detail": detail}
