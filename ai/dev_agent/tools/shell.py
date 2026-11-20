"""The `shell` tool: run a command line (chaining and pipes allowed) in the project. Safe commands run at once; the owner is asked only for risky ones (guard/shell.py).
A file a command changes (sed -i, a generator script, npm run build output ...) is found afterwards with a read-only `git status` comparison and put in the task ledger
with its original content, so the diff, the checks and the report know about it; a PROTECTED or forbidden file changed this way is reported loudly."""

from __future__ import annotations

import hashlib
import shutil
import subprocess

from ai.dev_agent.guard.shell import classify_line
from ai.dev_agent.tools import runner
from ai.dev_agent.tools.registry import ToolError, schema, tool


def _status(project) -> dict[str, tuple] | None:
    """{path: (size, mtime_ns)} of every changed or untracked file according to git, or None when git cannot tell (no repo, no git)."""
    if not shutil.which("git") or not (project.root / ".git").exists():
        return None
    try:
        out = subprocess.run(["git", "-c", "core.quotepath=off", "status", "--porcelain", "-z", "-uall"], cwd=project.root, capture_output=True, timeout=60, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    found = {}
    entries = out.decode("utf-8", "replace").split("\0")
    skip = False
    for entry in entries:
        if skip:   # the old name of a rename
            skip = False
            continue
        if len(entry) < 4:
            continue
        rel = entry[3:]
        skip = entry[0] in "RC"
        try:
            st = (project.root / rel).stat()
            found[rel] = (st.st_size, st.st_mtime_ns)
        except OSError:
            found[rel] = (-1, 0)   # deleted
    return found


def _head_blob(project, rel: str) -> bytes | None:
    try:
        return subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=project.root, capture_output=True, timeout=60, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def _record(ctx, before: dict, after: dict) -> list[str]:
    """Ledger entries for files whose git state changed during the command. Returns warnings (protected/forbidden/internal files)."""
    warnings = []
    for rel, sig in after.items():
        if before.get(rel) == sig or ctx.project.internal_reason(rel):
            continue
        try:
            full = ctx.project.root / rel
            deleted = sig[0] == -1
            if ctx.ledger:
                if rel not in ctx.ledger.data.get("snapshots", {}) and rel not in before:   # clean before the command: git HEAD holds its original (None = a new file)
                    ctx.ledger.snapshot_original(rel, _head_blob(ctx.project, rel))
                digest = None if deleted else hashlib.sha256(full.read_bytes()).hexdigest()
                ctx.ledger.record_file(rel, "deleted" if deleted else "written", None, digest, ctx.package, "changed by a shell command")
            reason = ctx.project.forbidden_reason(rel) or ctx.project.protected_reason(rel) or ctx.project.secret_reason(rel)
            if reason:
                warnings.append(f"{rel} ({reason})")
        except OSError:
            continue
    return warnings


def execute_line(ctx, line: str, reason: str = "", timeout: int | None = None) -> dict:
    decision = classify_line(line, ctx.project, ctx.settings)
    if decision.action == "deny":
        raise ToolError(f"blocked: {decision.reason}")
    if decision.action == "ask":
        why = f"{reason or 'no reason given'} | {decision.reason}"
        if not ctx.ask("command", f"cmd:{line}", f"run `{line}` ({why})"):
            raise ToolError(f"the owner did not approve `{line}` ({decision.reason}); find another way or report it")
    limit = ctx.settings["command_timeout_s"]
    before = _status(ctx.project)
    result = runner.run([line], ctx.project.root, min(timeout or limit, limit), ctx.settings["max_tool_result_chars"], cancel=ctx.cancel, shell_line=line)
    ctx.emit({"type": "command", "command": line[:300], "status": result["status"], "duration_s": result["duration_s"]})
    out = {"command": line, **result}
    after = _status(ctx.project) if before is not None else None
    if before is not None and after is not None:
        warnings = _record(ctx, before, after)
        changed = sorted(p for p in after if before.get(p) != after[p])
        if changed:
            out["files_changed"] = changed[:30]
        if warnings:
            out["warning"] = "this command changed protected/forbidden files: " + ", ".join(warnings) + ". The owner is told in the report; do not do this again."
            if ctx.ledger:
                ctx.ledger.event("shell_touched_guarded_files", files=warnings)
    return out


@tool("shell", "args {command, reason?, timeout_s?}: run a command line in the project through the system shell (cmd on Windows, sh elsewhere). Use it for tests, linters, builds, "
      "scripts and anything else. `&&`, `||` and `|` are allowed, one line. Safe commands run at once; risky ones (deleting/moving files, installs, network, paths outside the project, "
      "protected files) ask the owner, so give a `reason`. git is read-only. Files it changes are tracked.", mutating=True,
      params=schema({"command": {"type": "string", "description": "the command line"}, "reason": {"type": "string", "description": "why (shown when approval is needed)"},
                     "timeout_s": {"type": "integer", "description": "optional time limit in seconds"}}, ["command"]))
def shell(ctx, args):
    line = str(args.get("command") or "").strip()
    timeout = args.get("timeout_s")
    return execute_line(ctx, line, str(args.get("reason") or ""), int(timeout) if isinstance(timeout, int) and timeout > 0 else None)
