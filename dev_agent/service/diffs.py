"""Diffs for a task: the content a file had before the agent touched it (from the ledger snapshot) against what is on disk now.
Only files recorded in the task's ledger can be read through this module, never arbitrary paths."""

from __future__ import annotations

import difflib

from ..core.project import PathError

MAX_BYTES = 400_000


class NotInTask(KeyError):
    pass


def _check(ledger, project, raw: str) -> str:
    rel, _ = project.resolve(raw)
    if rel not in ledger.data["files"] and rel not in ledger.data.get("snapshots", {}):
        raise NotInTask(f"{rel} is not part of task {ledger.id}")
    if project.secret_reason(rel) or project.forbidden_reason(rel):
        raise PathError(f"{rel} is never shown")
    return rel


def _text(data: bytes | None):
    """(text or None, is_binary, truncated)"""
    if data is None:
        return None, False, False
    if b"\0" in data[:8000]:
        return None, True, False
    cut = len(data) > MAX_BYTES
    try:
        return data[:MAX_BYTES].decode("utf-8").replace("\r\n", "\n"), False, cut
    except UnicodeDecodeError:
        return None, True, False


def original_bytes(ledger, project, raw: str):
    rel = _check(ledger, project, raw)
    return ledger.original(rel)[1]


def current_bytes(ledger, project, raw: str):
    rel, full = project.resolve(raw)
    _check(ledger, project, rel)
    return full.read_bytes() if full.is_file() else None


def _unified(old: str | None, new: str | None, name_a: str, name_b: str, context: int = 3) -> list[str]:
    """The one place a diff is computed (file_diff and line_counts both use it). Real lines only: splitlines() has no phantom empty last line,
    which a plain split("\\n") adds after a trailing newline and which showed up as an extra +/- line."""
    lines = list(difflib.unified_diff((old or "").splitlines(), (new or "").splitlines(), name_a, name_b, lineterm="", n=context))
    if not lines and old is not None and new is not None and old != new:
        return ["\\ only the line endings or the trailing newline changed"]
    return lines


def file_diff(ledger, project, raw: str) -> dict:
    rel = _check(ledger, project, raw)
    known, before = ledger.original(rel)
    full = project.root / rel
    after = full.read_bytes() if full.is_file() else None
    old, old_bin, cut_a = _text(before)
    new, new_bin, cut_b = _text(after)
    entry = ledger.data["files"].get(rel, {})
    out = {"path": rel, "state": entry.get("state", "unknown"), "detail": entry.get("detail", ""), "known_original": known,
           "existed_before": before is not None, "exists_now": after is not None, "binary": old_bin or new_bin, "truncated": cut_a or cut_b,
           "renamed_from": ledger.data.get("snapshots", {}).get(rel, {}).get("from"), "diff": ""}
    if not out["binary"]:
        out["diff"] = "\n".join(_unified(old, new, f"a/{rel}" if before is not None else "/dev/null", f"b/{rel}" if after is not None else "/dev/null"))
    return out


def line_counts(ledger, project, raw: str):
    """(added, removed) line counts, or None when there is no text diff (binary, too large, unreadable). Counts real lines, not a trailing newline."""
    rel = _check(ledger, project, raw)
    known, before = ledger.original(rel)
    full = project.root / rel
    after = full.read_bytes() if full.is_file() else None
    (old, old_bin, cut_a), (new, new_bin, cut_b) = _text(before), _text(after)
    if old_bin or new_bin or cut_a or cut_b:
        return None
    lines = _unified(old, new, "a", "b", 0)
    body = lines[2:] if len(lines) > 1 else []                      # skip the two ---/+++ header lines by position, not by prefix (a real line can start with ++ or --)
    return sum(1 for line in body if line[:1] == "+"), sum(1 for line in body if line[:1] == "-")
