"""Shell guard decisions: redirects, line classification, safe paths."""

from __future__ import annotations

from pathlib import Path

from ai.dev_agent.guard import ALLOW, Decision, ask, deny
from ai.dev_agent.guard.commands import CommandError, classify, exe_name
from .parsing import SAFE, parse


def _redirect(project, target: str, settings: dict) -> Decision:
    from ai.dev_agent.guard import paths
    try:
        rel, _ = project.resolve(target)
    except Exception:   # PathError: absolute path, '..', drive letter, reserved name
        return ask(f"output redirected to '{target}', a path outside the project")
    decision = paths.check_write(project, rel, "edit", None, {**settings, "ask_outside_plan": False})
    if decision.action == "deny" and decision.reason.startswith("no approved plan"):
        protected = project.protected_reason(rel)
        reason = project.forbidden_reason(rel) or project.secret_reason(rel)
        if reason:
            return deny(f"output redirected into {rel}: {reason}")
        if protected and settings.get("ask_protected_files", True):
            return ask(f"output redirected into {rel}: PROTECTED ({protected})")
        return ask(f"output redirected into the file {rel}: use write_file so the change is tracked")
    return decision


def classify_line(line: str, project, settings: dict | None = None, windows: bool | None = None) -> Decision:
    """allow | ask | deny for a whole command line."""
    settings = settings or {}
    try:
        parsed = parse(line, windows)
    except CommandError as exc:
        return deny(str(exc))
    if not parsed.commands:
        return deny("empty command")
    asks: list[str] = []
    unlisted = True
    for argv in parsed.commands:
        name = exe_name(argv[0])
        decision = ALLOW if name in SAFE and not any(a in ("-delete", "-exec", "-execdir", "-fprint", "--output") for a in argv[1:]) and classify_safe_paths(argv, project) else classify(
            [name, *argv[1:]] if name == "python" else argv, project.root, project.config["commands"])
        if decision.action == "deny":
            return decision
        if decision.action == "ask":
            asks.append(decision.reason)
            unlisted = unlisted and decision.kind == "unlisted"
    if settings.get("ask_protected_files", True):
        for argv in parsed.commands:
            for tok in argv[1:]:
                try:
                    rel, _ = project.resolve(tok.split("=", 1)[-1])
                except Exception:   # not a path inside the project
                    continue
                if project.protected_reason(rel):
                    asks.append(f"the command names the PROTECTED file {rel} ({project.protected_reason(rel)})")
                    unlisted = False
    for target in parsed.redirects:
        decision = _redirect(project, target, settings)
        if decision.action == "deny":
            return decision
        if decision.action == "ask":
            asks.append(decision.reason)
            unlisted = False
    asks += parsed.notes
    unlisted = unlisted and not parsed.notes
    if not asks:
        return ALLOW
    if unlisted and not settings.get("ask_other_commands", True):
        return ALLOW   # the owner switched the approval off: harmless commands that are only missing from the allow list run
    return Decision("ask", "; ".join(dict.fromkeys(asks)), "unlisted" if unlisted else "")


def classify_safe_paths(argv: list[str], project) -> bool:
    """A harmless read-only command still asks when it points outside the project (e.g. `cat C:\\Windows\\...`)."""
    from ai.dev_agent.guard.commands import _path_escape
    return not _path_escape(argv[1:], Path(project.root))
