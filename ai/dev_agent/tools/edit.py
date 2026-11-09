"""edit_files: multi-file edit with SHA checks. Validation is all-or-nothing; the write phase re-checks every sha under locks, rolls back on a
partial failure, and the result reports the exact final state of every file."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass

from ai.dev_agent.core import fsutil
from ai.dev_agent.core.project import PathError
from ai.dev_agent.tools.registry import ToolError, tool

MAX_FILES = 60
MAX_TEXT = 60000


@dataclass
class Prep:
    rel: str
    abs: object
    before: bytes | None
    new: bytes
    sha_before: str
    sha_after: str
    state: str = "pending"
    detail: str = ""


def _syntax(rel: str, text: str) -> str:
    try:
        if rel.endswith(".py"):
            ast.parse(text)
        elif rel.endswith(".json"):
            json.loads(text)
    except (SyntaxError, ValueError) as exc:
        return f"{type(exc).__name__}: {exc}"
    return ""


def _prepare(ctx, item: dict):
    """A Prep, or (rel, reason) when this file cannot be edited."""
    rel, full = ctx.project.resolve(item.get("path"))
    exists = full.is_file()
    if full.exists() and not exists:
        return rel, "not a regular file"
    ok, why = ctx.allow_write(rel, "edit" if exists else "create")
    if not ok:
        return rel, why
    before = fsutil.read_bytes(full) if exists else None
    sha_b = fsutil.sha(before) if before is not None else ""
    expect = item.get("expect_sha") or ctx.seen.get(rel)
    if expect and exists and expect != sha_b:
        return rel, "conflict: the file changed since it was read (sha mismatch); read it again before editing"
    if "content" in item:
        if exists and not item.get("overwrite"):
            return rel, "the file exists: use `replacements`, or set overwrite=true to replace it completely"
        text, crlf = str(item["content"]), (fsutil.decode(before)[1] if exists else False)
        if len(text) > MAX_TEXT * 4:
            return rel, "content too large for one edit"
    else:
        reps = item.get("replacements")
        if not exists or not isinstance(reps, list) or not reps:
            return rel, "give `replacements` [{old,new}] for an existing file, or `content` for a new one"
        text, crlf = fsutil.decode(before)
        for number, rep in enumerate(reps, 1):
            old, new = str(rep.get("old", "")), str(rep.get("new", ""))
            if not old or len(old) > MAX_TEXT or len(new) > MAX_TEXT:
                return rel, f"replacement {number}: `old` is empty or too large"
            if old == new:
                return rel, f"replacement {number}: old equals new"
            found = text.count(old)
            if found != 1:
                return rel, f"replacement {number}: `old` must match exactly once, found {found} times; include more surrounding text"
            text = text.replace(old, new, 1)
    problem = _syntax(rel, text)
    if problem:
        return rel, f"the result would not parse ({problem})"
    data = fsutil.encode(text, crlf)
    prep = Prep(rel, full, before, data, sha_b, fsutil.sha(data))
    if before == data:
        prep.state, prep.detail = "unchanged", "content already identical"
    return prep


def _current(p: Prep):
    return fsutil.read_bytes(p.abs) if p.abs.is_file() else None


def _rollback(p: Prep) -> None:
    cur = _current(p)
    cur_sha = fsutil.sha(cur) if cur is not None else None
    old_sha = p.sha_before if p.before is not None else None
    if cur_sha == p.sha_after:
        try:
            if p.before is None:
                p.abs.unlink()
            else:
                fsutil.atomic_write(p.abs, p.before)
            p.state, p.detail = "rolled_back", "restored to the content before this edit"
        except OSError as exc:
            p.state, p.detail = "rollback_failed", f"could not restore: {exc}"
    elif cur_sha == old_sha:
        p.state, p.detail = "unchanged", "never changed"
    else:
        p.state, p.detail = "rollback_failed", "differs from both the old and the new content (changed by someone else); left as it is"


def _commit(ctx, preps: list[Prep]) -> str:
    todo = [p for p in preps if p.state == "pending"]
    error = ""
    with fsutil.lock_many(ctx.project.lock_dir, [p.rel for p in todo]):
        for p in todo:   # nobody may have touched a file between validation and now
            cur = _current(p)
            if (cur is None) != (p.before is None) or (cur is not None and fsutil.sha(cur) != p.sha_before):
                p.state, p.detail = "conflict", "modified by someone else after validation; nothing was written for any file"
        if any(p.state == "conflict" for p in todo):
            for p in todo:
                if p.state == "pending":
                    p.state, p.detail = "unchanged", "not written: another file changed concurrently"
            return "a file was modified concurrently; nothing was written"
        written = []
        for p in todo:
            if ctx.ledger:
                ctx.ledger.snapshot_original(p.rel, p.before)   # the original must be safe before anything is written
            try:
                fsutil.atomic_write(p.abs, p.new)
                if fsutil.sha(_current(p) or b"") != p.sha_after:
                    raise OSError("content differs after writing")
                p.state = "written"
                written.append(p)
            except Exception as exc:
                error = f"{p.rel}: {type(exc).__name__}: {exc}"
                reason = str(exc)
                _rollback(p)   # the write may have landed even though verification failed
                p.detail = f"write failed ({reason}); {p.detail}"
                p.state = "failed" if p.state == "unchanged" else p.state
                break
        if error:
            for p in reversed(written):
                _rollback(p)
            for p in todo:
                if p.state == "pending":
                    p.state, p.detail = "unchanged", "not written: an earlier file failed"
    return error


def _report(ctx, preps: list[Prep], extra: list[dict], error: str) -> dict:
    files = list(extra)
    for p in preps:
        cur = _current(p)
        now = fsutil.sha(cur) if cur is not None else None
        files.append({"path": p.rel, "state": p.state, "sha_before": p.sha_before or None, "sha_now": now, "detail": p.detail})
        if p.state == "written":
            ctx.seen[p.rel] = p.sha_after
        if ctx.ledger:
            ctx.ledger.record_file(p.rel, p.state, p.sha_before or None, now, ctx.package, p.detail)
    return {"ok": not error and all(f["state"] in ("written", "unchanged") for f in files), "error": error, "files": files}


@tool("edit_files", "args {edits:[{path, replacements:[{old,new}] | content[,overwrite], expect_sha?}]}: edit/create several files in ONE call. "
      "All-or-nothing: if any file is rejected nothing is written. `old` must match exactly once. Result lists every file's exact state.", mutating=True)
def edit_files(ctx, args):
    items = args.get("edits")
    if not isinstance(items, list) or not items or len(items) > MAX_FILES:
        raise ToolError(f"`edits` must be a list of 1-{MAX_FILES} file edits")
    preps, rejected, paths = [], [], set()
    for item in items:
        try:
            got = _prepare(ctx, item) if isinstance(item, dict) else ("?", "each edit must be an object")
        except (PathError, UnicodeDecodeError) as exc:
            got = (str(item.get("path")) if isinstance(item, dict) else "?", str(exc) or "binary file")
        if isinstance(got, tuple):
            rejected.append({"path": got[0], "state": "rejected", "detail": got[1]})
        elif got.rel in paths:
            rejected.append({"path": got.rel, "state": "rejected", "detail": "the same file appears twice in one call"})
        else:
            paths.add(got.rel)
            preps.append(got)
    if rejected:
        for p in preps:
            p.detail = p.detail or "not written because another file in this call was rejected"
            p.state = "unchanged"
        return _report(ctx, preps, rejected, "rejected: nothing was written (all-or-nothing)")
    return _report(ctx, preps, [], _commit(ctx, preps))
