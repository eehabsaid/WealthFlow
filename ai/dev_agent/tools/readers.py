"""Read-only tools: search the index, grep, read a file, check a change plan."""

from __future__ import annotations

import fnmatch
import os
import re

from ai.dev_agent.core import fsutil
from ai.dev_agent.core.project import ALWAYS_EXCLUDE
from ai.dev_agent.guard import paths
from ai.dev_agent.tools.registry import ToolError, tool

MAX_READ_LINES = 400


@tool("search_index", "args {query}: files, classes and functions in the repo index that match words of the query")
def search_index(ctx, args):
    query = str(args.get("query") or "").strip()
    if not query:
        raise ToolError("give a `query`")
    return {"results": ctx.index.search(query, 15)}


@tool("grep", "args {pattern, glob?, max_results?}: regex search over text files; returns path:line: text")
def grep(ctx, args):
    try:
        rx = re.compile(str(args.get("pattern") or ""))
    except re.error as exc:
        raise ToolError(f"bad regex: {exc}") from exc
    glob, limit = str(args.get("glob") or "*"), min(int(args.get("max_results") or 50), 200)
    skip = ALWAYS_EXCLUDE | set(ctx.project.config["index_exclude"])
    hits = []
    for folder, dirs, names in os.walk(ctx.project.root):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in names:
            full = os.path.join(folder, name)
            rel = os.path.relpath(full, ctx.project.root).replace("\\", "/")
            if not fnmatch.fnmatch(rel, glob) and not fnmatch.fnmatch(name, glob):
                continue
            if paths.check_read(ctx.project, rel).action != "allow" or os.path.getsize(full) > 1_000_000:
                continue
            try:
                with open(full, encoding="utf-8") as handle:
                    for number, line in enumerate(handle, 1):
                        if rx.search(line):
                            hits.append(f"{rel}:{number}: {line.strip()[:200]}")
                            if len(hits) >= limit:
                                return {"matches": hits, "truncated": True}
            except (UnicodeDecodeError, OSError):
                continue
    return {"matches": hits, "truncated": False}


@tool("read_file", f"args {{path, start?, end?}}: numbered lines (max {MAX_READ_LINES} per call) plus the file's sha")
def read_file(ctx, args):
    rel, full = ctx.project.resolve(args.get("path"))
    decision = paths.check_read(ctx.project, rel)
    if decision.action != "allow":
        raise ToolError(decision.reason)
    if not full.is_file():
        raise ToolError(f"no such file: {rel}")
    data = fsutil.read_bytes(full)
    text, _ = fsutil.decode(data)
    lines = text.split("\n")
    start = max(1, int(args.get("start") or 1))
    end = min(len(lines), int(args.get("end") or start + MAX_READ_LINES - 1), start + MAX_READ_LINES - 1)
    digest = fsutil.sha(data)
    ctx.seen[rel] = digest
    body = "\n".join(f"{n}\t{lines[n - 1]}" for n in range(start, end + 1))
    return {"path": rel, "sha": digest, "total_lines": len(lines), "start": start, "end": end, "text": body}


@tool("plan_check", "args {files}: per file protected reason, line count, importing files, covering test module")
def plan_check(ctx, args):
    files = [str(f) for f in (args.get("files") or [])][:30]
    if not files:
        raise ToolError("give `files`")
    limit, rows, tests, approvals = ctx.project.config["max_file_lines"], [], set(), []
    idx = ctx.index.get()
    for raw in files:
        rel, full = ctx.project.resolve(raw)
        lines = idx.get(rel, {}).get("lines") or (fsutil.read_bytes(full).count(b"\n") + 1 if full.is_file() else 0)
        reason, module = ctx.project.protected_reason(rel), ctx.project.test_module(rel)
        stem = rel.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        callers = [c for c in ctx.index.callers(stem) if c != rel]
        if module:
            tests.add(module)
        if reason:
            approvals.append(rel)
        rows.append({"file": rel, "exists": full.is_file(), "lines": lines, "over_limit": limit > 0 and lines > limit, "protected": reason,
                     "tests": module, "callers": callers[:15], "caller_count": len(callers)})
    return {"files": rows, "tests_to_run": sorted(tests), "needs_owner_approval": approvals, "max_file_lines": limit}
