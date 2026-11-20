"""General file tools: write_file, edit_file (one exact replacement), glob, list_dir. They reuse edit_files (tools/edit.py), so every write keeps the same guards:
SHA check against what the model read, all-or-nothing validation, locks, atomic write, rollback, ledger record, plan scope, protected/forbidden files."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from ai.dev_agent.core.project import ALWAYS_EXCLUDE
from ai.dev_agent.guard import paths
from ai.dev_agent.tools import edit, limits
from ai.dev_agent.tools.registry import ToolError, schema, tool


def _one(ctx, item: dict) -> dict:
    res = edit.edit_files(ctx, {"edits": [item]})
    row = res["files"][0] if res["files"] else {}
    if row.get("state") in ("written", "unchanged"):
        return {"ok": True, "path": row["path"], "state": row["state"], "sha": row.get("sha_now"), "detail": row.get("detail", "")}
    raise ToolError(row.get("detail") or res.get("error") or "the edit was not applied")


@tool("write_file", "args {path, content, overwrite?}: create a file with this content. An existing file is replaced only with overwrite=true AND only after you read it "
      "(read_file) so the SHA check works. For small changes use edit_file.", mutating=True,
      params=schema({"path": "string", "content": {"type": "string", "description": "the complete file content"}, "overwrite": {"type": "boolean", "description": "replace an existing file"}}, ["path", "content"]))
def write_file(ctx, args):
    rel, full = ctx.project.resolve(args.get("path"))
    if full.is_file() and args.get("overwrite") and rel not in ctx.seen:
        raise ToolError(f"read {rel} with read_file first: overwriting is SHA-checked against what you read")
    return _one(ctx, {"path": rel, "content": str(args.get("content", "")), **({"overwrite": True} if args.get("overwrite") else {})})


@tool("edit_file", "args {path, old, new}: replace the text `old` with `new` in one file. `old` must match EXACTLY once (include surrounding lines to make it unique). "
      "Read the file first (SHA-checked). Several files at once: edit_files.", mutating=True,
      params=schema({"path": "string", "old": {"type": "string", "description": "exact text to replace, must occur once"}, "new": {"type": "string", "description": "replacement text"}}, ["path", "old", "new"]))
def edit_file(ctx, args):
    return _one(ctx, {"path": args.get("path"), "replacements": [{"old": str(args.get("old", "")), "new": str(args.get("new", ""))}]})


def _walk(ctx, base: Path):
    skip = ALWAYS_EXCLUDE | set(ctx.project.config["index_exclude"])
    for folder, dirs, names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in skip and Path(folder, d) != ctx.project.agent_dir)   # the agent's own folder is internal
        yield folder, dirs, [n for n in sorted(names) if paths.check_read(ctx.project, os.path.relpath(os.path.join(folder, n), ctx.project.root).replace("\\", "/")).action == "allow"]


@tool("glob", "args {pattern, path?}: file paths matching a glob such as **/*.py or app/*/models.py (relative to the project, newest first is not guaranteed; sorted by path)",
      params=schema({"pattern": {"type": "string", "description": "glob, e.g. **/*.py"}, "path": {"type": "string", "description": "folder to search (default: the project)"}}, ["pattern"]))
def glob(ctx, args):
    pattern = str(args.get("pattern") or "").replace("\\", "/")
    base_rel = str(args.get("path") or "").strip().strip("/")
    _, base = ctx.project.resolve(base_rel) if base_rel else ("", ctx.project.root)
    cap, hits = limits.of(ctx.settings)["glob_cap"], []
    for folder, _, names in _walk(ctx, base):
        for name in names:
            rel = os.path.relpath(os.path.join(folder, name), ctx.project.root).replace("\\", "/")
            if paths.check_read(ctx.project, rel).action != "allow":
                continue
            inside = rel[len(base_rel) + 1:] if base_rel and rel.startswith(base_rel + "/") else rel
            if fnmatch.fnmatch(inside, pattern) or fnmatch.fnmatch(name, pattern) or (pattern.startswith("**/") and fnmatch.fnmatch(inside, pattern[3:])):
                hits.append(rel)
                if len(hits) >= cap:
                    return {"files": hits, "truncated": True}
    return {"files": hits, "truncated": False}


@tool("list_dir", "args {path?, depth?}: the files and folders of a directory (default: the project root; depth 1-3, default 1). Folders end with /",
      params=schema({"path": {"type": "string", "description": "folder (default: the project root)"}, "depth": {"type": "integer", "description": "1-3"}}))
def list_dir(ctx, args):
    rel = str(args.get("path") or "").strip().strip("/")
    _, base = ctx.project.resolve(rel) if rel else ("", ctx.project.root)
    if not base.is_dir():
        raise ToolError(f"not a folder: {rel or '.'}")
    depth, cap, rows = max(1, min(int(args.get("depth") or 1), 3)), limits.of(ctx.settings)["glob_cap"], []
    for folder, dirs, names in _walk(ctx, base):
        level = len(Path(folder).relative_to(base).parts)
        if level >= depth:
            dirs[:] = []
            if level > depth:
                continue
        here = os.path.relpath(folder, ctx.project.root).replace("\\", "/")
        prefix = "" if here == "." else here + "/"
        rows += [prefix + d + "/" for d in dirs] + [prefix + n for n in names]
        if len(rows) >= cap:
            return {"entries": rows[:cap], "truncated": True}
    return {"entries": rows, "truncated": False}
