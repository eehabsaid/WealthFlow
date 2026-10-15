"""More sysadmin-only, read-only code tools for the Agent: callers, git history/blame, and a UI -> JS -> URL -> view -> model trace.

Same guard and the same redaction as code_tools.py; failures come back as {"error": ...} with a hint.
"""

from __future__ import annotations

import re
import subprocess

from . import code_tools as ct
from . import paths

_DEF_LINE = re.compile(r"^\s*(?:async\s+def|def|class|function)\s")
_GIT_TIMEOUT_S = 10
_LAYERS = (   # (result key, folder, file globs)
    ("frontend", "static/js", ["*.js"]), ("templates", "templates", ["*.html"]), ("urls", "core/urls", ["*.py"]),
    ("views", "core/views", ["*.py"]), ("services", "core/services", ["*.py"]), ("models", "core/models", ["*.py"]))


def callers(user, params):
    denied = ct._guard(user)
    if denied:
        return denied
    name = str(params.get("symbol") or "").strip()
    if not re.fullmatch(r"[A-Za-z_$][\w$.]*", name):
        return {"error": "symbol must be a function, class or variable name such as ExpenseService or applyReverse"}
    rx = re.compile(rf"(?<![\w$]){re.escape(name.rsplit('.', 1)[-1])}(?![\w$])")
    matches, _total, scanned = ct._search(rx, paths.BASE, ["*.py", "*.js", "*.html"], 100)
    uses = [m for m in matches if not _DEF_LINE.match(m["text"])]
    by_file: dict = {}
    for m in uses:
        by_file[m["file"]] = by_file.get(m["file"], 0) + 1
    out = {"symbol": name, "usages": uses[:40], "files": by_file, "files_scanned": scanned}
    if not uses:
        out["note"] = "no usage found outside its definition; it may be called dynamically or only from templates"
    return out


def _git(args: list[str]):
    try:
        done = subprocess.run(["git", *args], cwd=paths.BASE, capture_output=True, text=True, timeout=_GIT_TIMEOUT_S, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def git_history(user, params):
    denied = ct._guard(user)
    if denied:
        return denied
    try:
        target = paths.resolve(params.get("path", ""))
    except paths.PathError as exc:
        return {"error": str(exc)}
    if not target.is_file():
        return {"error": "path must be a file; use app_list_dir or app_find_files first"}
    rel = paths.rel(target)
    if str(params.get("action") or "log").lower() == "blame":
        start = ct._int(params.get("start_line"), 1, 1, 100000)
        end = ct._int(params.get("end_line"), start + 19, start, start + 79)
        raw = _git(["blame", "--date=short", "-L", f"{start},{end}", "--", rel])
        if raw is None:
            return {"error": "git blame is not available here (no repository on this server, or the line range is outside the file)"}
        return {"path": rel, "start_line": start, "end_line": end, "blame": [paths.redact(x)[:200] for x in raw.splitlines()]}
    count = ct._int(params.get("limit"), 8, 1, 15)
    raw = _git(["log", f"-{count}", "--date=short", "--pretty=format:%h|%ad|%an|%s", "--", rel])
    if raw is None:
        return {"error": "git history is not available here (no repository on this server)"}
    commits = [dict(zip(("commit", "date", "author", "subject"), line.split("|", 3))) for line in raw.splitlines() if line]
    return {"path": rel, "commits": commits, **({} if commits else {"note": "no commits touch this file"})}


def trace_feature(user, params):
    """Where a feature lives, layer by layer: UI labels -> JS -> templates -> URLs -> views -> services -> models."""
    denied = ct._guard(user)
    if denied:
        return denied
    term = str(params.get("feature") or "").strip()
    if len(term) < 3:
        return {"error": "feature is required (at least 3 characters), e.g. 'exchange rates' or 'gold_price'"}
    words = {term, term.replace(" ", "_"), term.replace(" ", "")}
    rx = re.compile("|".join(re.escape(w) for w in sorted(words)), re.IGNORECASE)
    out: dict = {"feature": term}
    for key, folder, globs in _LAYERS:
        try:
            root = paths.resolve(folder)
        except paths.PathError:
            continue
        hits, total, _ = ct._search(rx, root, globs, 6)
        out[key] = {"hits": hits, "total": total}
    out["note"] = "open the most relevant hit of each layer with app_read_file to confirm before answering"
    return out
