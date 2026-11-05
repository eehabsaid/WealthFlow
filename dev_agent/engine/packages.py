"""Split an approved plan into work packages that each fit the context window (150K minus the reserve and fixed overhead).
Cost estimate per step: base overhead + for each file its size twice (read it, then edit it) at chars/4."""

from __future__ import annotations

SYSTEM_OVERHEAD = 9000   # system prompt, tool list, ledger brief
STEP_BASE = 3000
SHARE = 0.6              # a package may use at most this share of the free window; the rest is conversation growth


def file_tokens(project, rel: str) -> int:
    try:
        size = (project.root / rel).stat().st_size
    except OSError:
        size = 2000
    return max(size, 2000) // 4 * 2


def capacity(window: int, reserve: int) -> int:
    return int((window - reserve - SYSTEM_OVERHEAD) * SHARE)


def split(project, plan: dict, window: int, reserve: int) -> list[dict]:
    cap, packages, cur = capacity(window, reserve), [], None
    for step in plan["steps"]:
        cost = STEP_BASE + sum(file_tokens(project, f) for f in step["files"])
        if cur is None or cur["est_tokens"] + cost > cap:
            cur = {"id": f"P{len(packages) + 1}", "title": step["title"], "steps": [], "files": [], "est_tokens": 0, "status": "pending", "summary": "", "oversize": False}
            packages.append(cur)
        cur["steps"].append(step["id"])
        cur["files"] = sorted(set(cur["files"]) | set(step["files"]))
        cur["est_tokens"] += cost
        cur["oversize"] = cur["est_tokens"] > cap
        if len(cur["steps"]) > 1:
            cur["title"] = f"{cur['title'].split(' + ')[0]} + {len(cur['steps']) - 1} more"
    return packages
