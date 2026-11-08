"""Turn a finished or stopped task into memory entries. Everything comes from the ledger (what really happened), never from the model's claims."""

from __future__ import annotations

import datetime

from . import store

NOT_A_LESSON = ("stopped by user", "interrupted:", "plan rejected")


def _short(text: str, n: int) -> str:
    return " ".join(str(text).split())[:n]


def _structure(ledger) -> str:
    added, removed, renamed = [], [], []
    for rel, f in sorted(ledger.data["files"].items()):
        if f["state"] == "deleted":
            removed.append(rel)
        elif f["state"] == "renamed":
            renamed.append(f"{rel} -> {f['detail'].removeprefix('renamed to ')}")
        elif f["state"] == "written" and not f.get("detail", "").startswith("renamed from") and ledger.original(rel) == (True, None):
            added.append(rel)
    parts = [label + ", ".join(items[:8]) for label, items in (("added ", added), ("removed ", removed), ("renamed ", renamed)) if items]
    return f"task {ledger.id}: " + "; ".join(parts) if parts else ""


def capture(ledger) -> None:
    """Called when a run ends. Never raises: memory is a help, it must not break a task."""
    d, project = ledger.data, ledger.project
    if d["status"] not in ("completed", "stopped", "answered", "rejected"):
        return
    try:
        goal = _short(d["goal"], 160)
        try:
            store.clean(goal)
        except store.MemoryRefused:
            goal = "(goal not stored: it looks like it contains a secret)"
        final = next((v for v in reversed(d["verification"]) if v["label"] == "final"), None)
        store.record_task(project, {"id": d["id"], "date": datetime.date.today().isoformat(), "goal": goal, "status": d["status"],
                                    "files": sorted(d["files"])[:12], "reason": _short(d["stop_reason"], 200),
                                    "checks": {r["step"]: r["status"] for r in final["results"]} if final else {}})
        if d["status"] == "stopped" and d["stop_reason"] and not d["stop_reason"].lower().startswith(NOT_A_LESSON):
            _add(project, "lessons", f"{goal[:80]} - stopped: {_short(d['stop_reason'], 240)}")
        for a in d["approvals"]:
            if not a["approved"]:
                _add(project, "decisions", f"owner refused ({a['kind']}): {_short(a['message'], 240)}")
        if d["status"] == "rejected":
            _add(project, "decisions", f"owner rejected the plan for: {goal[:200]}")
        if d["status"] == "completed" and (line := _structure(ledger)):
            _add(project, "architecture", line)
    except (OSError, ValueError, KeyError):
        return


def _add(project, kind: str, text: str) -> None:
    try:
        store.add(project, kind, text)
    except store.MemoryRefused:
        pass
