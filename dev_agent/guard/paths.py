"""File guard: which paths the agent may read or write. Rules come from coding_agent/config.json (forbidden, protected, secret_files); the agent's own
coding_agent/ folder is never writable by a task, and a work package may only change its own files."""

from __future__ import annotations

from . import ALLOW, Decision, ask, deny


def check_read(project, rel: str) -> Decision:
    reason = project.secret_reason(rel)
    if reason:
        return deny(f"secret file ({reason}); the agent never reads secrets")
    if rel == ".git" or rel.startswith(".git/"):
        return deny("read git history with the read-only git tool, not by opening .git")
    return ALLOW


def check_write(project, rel: str, op: str, scope) -> Decision:
    """op: edit | create | delete | rename. `scope` is the approved plan's PlanScope, or None while only planning (nothing may be written)."""
    reason = project.forbidden_reason(rel) or project.secret_reason(rel)
    if reason:
        return deny(f"{rel} is forbidden: {reason}")
    if scope is None:
        return deny("no approved plan yet: this phase is read-only")
    other = getattr(scope, "other_package", lambda _rel: "")(rel)
    if other:
        return deny(f"{rel} belongs to work package {other}, not to this package: leave it for {other} (the approved plan is unchanged)")
    if op in ("delete", "rename") and not scope.allows(op, rel):
        return deny(f"{op} of {rel} is not listed in the approved plan (deleting or renaming needs to be in the plan)")
    reasons = []
    protected = project.protected_reason(rel)
    if protected:
        reasons.append(f"PROTECTED ({protected})")
    if op in ("edit", "create") and not scope.allows(op, rel):
        reasons.append("not in the approved plan (scope change)")
    return ask(f"{op} {rel}: " + "; ".join(reasons)) if reasons else ALLOW
