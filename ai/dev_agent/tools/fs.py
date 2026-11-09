"""delete_file and rename_file: only for paths listed in the approved plan; protected files need the owner. After either, the result
lists files that still import the old name so the agent can fix them (imports and routes must keep working)."""

from __future__ import annotations

import os
import stat

from ai.dev_agent.core import fsutil
from ai.dev_agent.tools.registry import ToolError, tool


def _remove(path) -> None:
    try:
        os.remove(path)
    except PermissionError:   # Windows read-only attribute
        os.chmod(path, stat.S_IWRITE)
        os.remove(path)


def _stem(rel: str) -> str:
    return rel.rsplit("/", 1)[-1].rsplit(".", 1)[0]


@tool("delete_file", "args {path}: delete one file. Only if the approved plan lists it.", mutating=True)
def delete_file(ctx, args):
    rel, full = ctx.project.resolve(args.get("path"))
    if not full.is_file():
        raise ToolError(f"no such file: {rel}")
    ok, why = ctx.allow_write(rel, "delete")
    if not ok:
        raise ToolError(why)
    with fsutil.file_lock(ctx.project.lock_dir, rel):
        before = fsutil.sha(fsutil.read_bytes(full))
        if ctx.seen.get(rel) and ctx.seen[rel] != before:
            raise ToolError("conflict: the file changed since it was read; read it again")
        if ctx.ledger:
            ctx.ledger.snapshot_original(rel, fsutil.read_bytes(full))
        _remove(full)
    ctx.seen.pop(rel, None)
    if ctx.ledger:
        ctx.ledger.record_file(rel, "deleted", before, None, ctx.package, "")
    return {"ok": True, "path": rel, "state": "deleted", "sha_before": before, "still_imported_by": [c for c in ctx.index.callers(_stem(rel)) if c != rel][:20]}


@tool("rename_file", "args {from, to}: rename/move one file (never overwrites). Only if the approved plan lists the pair.", mutating=True)
def rename_file(ctx, args):
    src_rel, src = ctx.project.resolve(args.get("from"))
    dst_rel, dst = ctx.project.resolve(args.get("to"))
    if not src.is_file():
        raise ToolError(f"no such file: {src_rel}")
    if dst.exists():
        raise ToolError(f"{dst_rel} already exists; renaming never overwrites")
    for rel, op in ((src_rel, "rename"), (dst_rel, "create")):
        ok, why = ctx.allow_write(rel, op)
        if not ok:
            raise ToolError(why)
    if not ctx.scope.allows("rename", src_rel, dst_rel):
        raise ToolError(f"{src_rel} -> {dst_rel} is not listed in the approved plan")
    with fsutil.lock_many(ctx.project.lock_dir, [src_rel, dst_rel]):
        digest = fsutil.sha(fsutil.read_bytes(src))
        if ctx.seen.get(src_rel) and ctx.seen[src_rel] != digest:
            raise ToolError("conflict: the file changed since it was read; read it again")
        if ctx.ledger:
            ctx.ledger.snapshot_original(src_rel, fsutil.read_bytes(src))
            ctx.ledger.snapshot_alias(dst_rel, src_rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        fsutil.replace_retry(src, dst)
    ctx.seen.pop(src_rel, None)
    ctx.seen[dst_rel] = digest
    if ctx.ledger:
        ctx.ledger.record_file(src_rel, "renamed", digest, None, ctx.package, f"renamed to {dst_rel}")
        ctx.ledger.record_file(dst_rel, "written", None, digest, ctx.package, f"renamed from {src_rel}")
    return {"ok": True, "from": src_rel, "to": dst_rel, "sha": digest, "still_imported_by": [c for c in ctx.index.callers(_stem(src_rel)) if c != dst_rel][:20]}
