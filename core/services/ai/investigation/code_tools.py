"""Read-only source-code tools for the AI investigator: list, find, grep, find-definition, read.

Sysadmin only (the code is the product, not the customer's data) and switchable with AppSettings `ai_code_access`.
Every handler is `handler(user, params) -> dict`; failures are returned as {"error": ...} with a hint on what to try next,
so the model can correct itself instead of giving up.
"""

from __future__ import annotations

import fnmatch
import re

from core.models import AppSettings

from . import paths

DEFAULT_GLOBS = "*.py,*.js,*.html,*.css,*.json,*.md,*.txt,*.sh,*.yml,*.yaml,*.toml,*.ini,*.cfg"
MAX_READ_LINES, MAX_READ_CHARS = 220, 14_000
NO_ACCESS = ("Source-code access is limited to the system administrator. Use app_data_models / app_data_query for "
             "this user's data and app_knowledge_search for how the app works.")


def code_access_allowed(user) -> bool:
    """Source-code tools: only an app sysadmin (profile.is_sysadmin, NOT Django's is_superuser) and only while the
    global ai_code_access switch is on (default on)."""
    from core.authentication.utils.auth_utils import user_is_sysadmin

    on = str(AppSettings.get("ai_code_access", "true", user=None) or "true").strip().lower() not in ("false", "0", "no", "off")
    return bool(on and user_is_sysadmin(user))


def _guard(user):
    return None if code_access_allowed(user) else {"error": NO_ACCESS}


def _clip(text: str, n: int = 220) -> str:
    text = paths.redact(text.rstrip())
    return text if len(text) <= n else text[: n - 1] + "…"


def _globs(value) -> list[str]:
    return [g.strip() for g in str(value or DEFAULT_GLOBS).split(",") if g.strip()]


def _int(value, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def list_dir(user, params):
    denied = _guard(user)
    if denied:
        return denied
    try:
        target = paths.resolve(params.get("path", ""))
    except paths.PathError as exc:
        return {"error": str(exc)}
    if not target.is_dir():
        return {"error": f"'{params.get('path')}' is a file; use app_read_file"}
    entries = []
    for child in sorted(target.iterdir(), key=lambda c: (c.is_file(), c.name.lower())):
        if child.is_dir():
            if child.name in paths.BLOCKED_DIRS or child.name.startswith("."):
                continue
            entries.append(f"{child.name}/")
        elif not paths.is_blocked_name(child.name):
            entries.append(f"{child.name} ({child.stat().st_size} B)")
    return {"path": paths.rel(target), "entries": entries[:200], "total": len(entries), "truncated": len(entries) > 200}


def find_files(user, params):
    denied = _guard(user)
    if denied:
        return denied
    pattern = str(params.get("pattern") or "").strip().lower()
    if not pattern:
        return {"error": "pattern is required, e.g. '*balance*.py' or 'expense_service'"}
    try:
        root = paths.resolve(params.get("path", ""))
    except paths.PathError as exc:
        return {"error": str(exc)}
    wild = any(c in pattern for c in "*?[")

    def matches(path: str) -> bool:
        low = path.lower()
        if not wild:
            return pattern in low
        return fnmatch.fnmatch(low, pattern) or fnmatch.fnmatch(low.rsplit("/", 1)[-1], pattern)

    hits = [p for p, _ in paths.iter_files(root) if matches(p)]
    return {"pattern": pattern, "files": hits[:100], "total": len(hits), "truncated": len(hits) > 100}


def _compile(pattern: str, ignore_case: bool):
    flags = re.IGNORECASE if ignore_case else 0
    try:
        return re.compile(pattern, flags)
    except re.error:
        return re.compile(re.escape(pattern), flags)


def _search(rx, root, globs, max_results: int, context: int = 0):
    matches, total, scanned = [], 0, 0
    for path, _size in paths.iter_files(root):
        name = path.rsplit("/", 1)[-1]
        if not any(fnmatch.fnmatch(name, g) for g in globs):
            continue
        text = paths.read_text(paths.BASE / path)
        if text is None:
            continue
        scanned += 1
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if rx.search(line):
                total += 1
                if len(matches) < max_results:
                    item = {"file": path, "line": i + 1, "text": _clip(line)}
                    if context:
                        item["context"] = [_clip(x, 160) for x in lines[max(0, i - context): i + context + 1]]
                    matches.append(item)
    return matches, total, scanned


def grep(user, params):
    denied = _guard(user)
    if denied:
        return denied
    pattern = str(params.get("pattern") or "")
    if not pattern.strip():
        return {"error": "pattern is required (regex or plain text)"}
    try:
        root = paths.resolve(params.get("path", ""))
    except paths.PathError as exc:
        return {"error": str(exc)}
    ic = str(params.get("ignore_case", "true")).lower() not in ("false", "0", "no")
    matches, total, scanned = _search(_compile(pattern, ic), root, _globs(params.get("file_glob")),
                                      _int(params.get("max_results"), 40, 1, 100), _int(params.get("context"), 0, 0, 3))
    out = {"pattern": pattern, "matches": matches, "total_matches": total, "files_scanned": scanned}
    if total > len(matches):
        out["note"] = f"{total - len(matches)} more matches not shown; narrow with path= or file_glob="
    if not total:
        out["note"] = "no match; try a shorter or different spelling (snake_case vs camelCase) or a wider path"
    return out


def find_definition(user, params):
    denied = _guard(user)
    if denied:
        return denied
    name = str(params.get("symbol") or "").strip()
    if not re.fullmatch(r"[A-Za-z_$][\w$.]*", name):
        return {"error": "symbol must be a function, class or variable name such as ExpenseService or applyReverse"}
    esc = re.escape(name)
    rx = re.compile(rf"^\s*(?:async\s+def|def|class|function|const|let|var)\s+{esc}\b|^\s*(?:window\.)?[\w.]*\.{esc}\s*=|^\s*{esc}\s*=")
    matches, total, _ = _search(rx, paths.BASE, ["*.py", "*.js", "*.html"], 15)
    return {"symbol": name, "definitions": matches, "total": total} if total else {
        "symbol": name, "definitions": [], "note": "no definition found; use app_grep for usages or a partial name"}


def read_file(user, params):
    denied = _guard(user)
    if denied:
        return denied
    try:
        target = paths.resolve(params.get("path", ""))
    except paths.PathError as exc:
        return {"error": str(exc)}
    if target.is_dir():
        return {"error": f"'{params.get('path')}' is a directory; use app_list_dir"}
    text = paths.read_text(target)
    if text is None or target.stat().st_size > paths.MAX_FILE_BYTES:
        return {"error": "binary or too large to read; use app_grep to search inside it"}
    lines = text.splitlines()
    start = _int(params.get("start_line"), 1, 1, max(1, len(lines)))
    end = _int(params.get("end_line"), start + 119, start, start + MAX_READ_LINES - 1)
    chunk, used = [], 0
    for n in range(start, min(end, len(lines)) + 1):
        row = f"{n}: {paths.redact(lines[n - 1])}"
        if used + len(row) > MAX_READ_CHARS:
            break
        chunk.append(row)
        used += len(row) + 1
    last = start + len(chunk) - 1
    out = {"path": paths.rel(target), "start_line": start, "end_line": last, "total_lines": len(lines), "content": "\n".join(chunk)}
    if last < len(lines):
        out["note"] = f"more lines remain: call again with start_line={last + 1}"
    return out
