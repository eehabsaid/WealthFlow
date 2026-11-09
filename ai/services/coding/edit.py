"""In-app code editing for the sysadmin's Agent mode. The model only PROPOSES a change; it is written only when the sysadmin presses
Confirm on the card, and only if the file is still exactly as it was when proposed. Protected files, secrets, databases, migrations and
anything outside the project are refused here (edit those yourself in VS Code after `python scripts/agent_plan.py <file>`)."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re

from django.conf import settings

from ai.services.investigation import paths

from ai.services.coding import ROOT
from ai.services.coding.config import load, protected_reason

ALLOWED_EXT = (".py", ".js", ".css", ".html", ".json", ".md", ".txt", ".sh")
MAX_TEXT = 8000   # characters of one old_str / new_str / new file


class EditError(ValueError):
    pass


def enabled() -> bool:
    """Only the local development server may change code; a hosted (DEBUG off) app never does."""
    return bool(settings.DEBUG)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_path(raw) -> tuple[str, object]:
    """(repo-relative posix path, absolute Path) of a file that may be edited, or EditError."""
    text = str(raw or "").strip().replace("\\", "/")
    if text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        raise EditError("use a repo-relative path, not an absolute one")
    parts = [p for p in text.split("/") if p not in ("", ".")]
    if not parts or ".." in parts:
        raise EditError("give a repo-relative file path without '..'")
    target = (ROOT / "/".join(parts)).resolve()
    if ROOT not in target.parents:
        raise EditError("that path is outside the project")
    rel = target.relative_to(ROOT).as_posix()
    if any(p in paths.BLOCKED_DIRS or p.startswith(".") for p in parts) or paths.is_blocked_name(parts[-1]):
        raise EditError("that path is excluded (secrets, databases, binaries, vendor, generated or hidden files)")
    if not rel.lower().endswith(ALLOWED_EXT):
        raise EditError(f"only {', '.join(ALLOWED_EXT)} files can be edited")
    if reason := protected_reason(rel):
        raise EditError(f"{rel} is protected ({reason}). It needs the owner's approval: edit it yourself in VS Code after `python scripts/agent_plan.py {rel}`")
    return rel, target


def _read(target) -> str:
    with open(target, encoding="utf-8", newline="") as fh:
        return fh.read()


def _lines(text: str) -> int:
    return text.count("\n") + (0 if text.endswith("\n") or not text else 1)


def _syntax(rel: str, text: str) -> None:
    try:
        if rel.endswith(".py"):
            ast.parse(text)
        elif rel.endswith(".json"):
            json.loads(text)
    except (SyntaxError, ValueError) as exc:
        raise EditError(f"the result would not be valid {rel.rsplit('.', 1)[-1]}: {str(exc)[:160]}") from None


def _like(text: str, sample: str) -> str:
    """Write `text` with the line endings the file already uses."""
    return text.replace("\r\n", "\n").replace("\n", "\r\n") if "\r\n" in sample else text.replace("\r\n", "\n")


def _limit(rel: str, before: str, after: str) -> None:
    cap = load()["max_file_lines"]
    if rel.endswith((".py", ".js", ".css", ".html")) and _lines(after) > cap and _lines(after) > _lines(before):
        raise EditError(f"the file would have {_lines(after)} lines; the limit is {cap}. Put the new code in a new file instead")


def build(params: dict) -> dict:
    """Validate one proposed change and return what the card and the later write need. Nothing is written."""
    rel, target = check_path(params.get("path"))
    content, old, new = params.get("content"), params.get("old_str"), params.get("new_str")
    for text in (content, old, new):
        if isinstance(text, str) and len(text) > MAX_TEXT:
            raise EditError(f"keep one change under {MAX_TEXT} characters; make several smaller changes")
    if content is not None and not target.exists():
        content = _like(str(content), "")
        _limit(rel, "", content)
        _syntax(rel, content)
        return {"op": "add", "path": rel, "content": content, "old": "", "new": content, "lines": f"+{_lines(content)}"}
    if not target.is_file():
        raise EditError(f"{rel} does not exist; to create a file pass `content`")
    if content is not None:
        raise EditError(f"{rel} already exists; change it with old_str and new_str")
    if not isinstance(old, str) or not old or not isinstance(new, str):
        raise EditError("give `old_str` (the exact text to replace) and `new_str`")
    current = _read(target)
    old_l, new_l = _like(old, current), _like(new, current)
    if current.count(old_l) != 1:
        raise EditError(f"old_str must appear exactly once in {rel} (found {current.count(old_l)}); copy more surrounding lines from app_read_file")
    after = current.replace(old_l, new_l, 1)
    if after == current:
        raise EditError("nothing would change")
    _limit(rel, current, after)
    _syntax(rel, after)
    return {"op": "edit", "path": rel, "old_str": old_l, "new_str": new_l, "base_sha": sha(current), "old": old, "new": new,
            "lines": f"+{_lines(new)} / -{_lines(old)}"}


def apply(params: dict) -> str:
    """Write a confirmed change (re-checked: same rules, file unchanged since the proposal)."""
    rel, target = check_path(params.get("path"))
    if params.get("op") == "add":
        if target.exists():
            raise EditError(f"{rel} now exists; ask for the change again")
        text = str(params["content"])
        _syntax(rel, text)
        os.makedirs(target.parent, exist_ok=True)
    else:
        if not target.is_file():
            raise EditError(f"{rel} no longer exists")
        current = _read(target)
        if sha(current) != params.get("base_sha"):
            raise EditError(f"{rel} changed after it was proposed; ask for the change again")
        text = current.replace(params["old_str"], params["new_str"], 1)
        _syntax(rel, text)
    temp = f"{target}.wf_tmp"
    with open(temp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(temp, target)
    return f"{rel} written ({params.get('lines', '')}). Run app_run_checks on it."
