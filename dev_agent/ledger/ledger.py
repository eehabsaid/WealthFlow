"""The task ledger: goal, plan, work packages, per-file state, approvals, verification results and a short summary of finished work, saved
atomically after every change at coding_agent/tasks/<id>/ledger.json. Every work package starts from a brief built from it."""

from __future__ import annotations

import datetime
import hashlib
import json
import re

from ..core import fsutil

MAX_EVENTS = 300


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


class Ledger:
    def __init__(self, project, task_id: str, data: dict):
        self.project, self.id, self.data = project, task_id, data
        self.listener = None   # called with every ledger event, e.g. to stream it to a UI
        self.dir = project.agent_dir / "tasks" / task_id
        self.file = self.dir / "ledger.json"

    @classmethod
    def create(cls, project, goal: str) -> "Ledger":
        slug = re.sub(r"[^a-z0-9]+", "-", goal.lower()).strip("-")[:30] or "task"
        base = f"{datetime.datetime.now():%Y%m%d-%H%M%S}-{slug}"
        task_id, n = base, 1
        while (project.agent_dir / "tasks" / task_id).exists():
            n += 1
            task_id = f"{base}-{n}"
        data = {"id": task_id, "goal": goal, "created": _now(), "updated": _now(), "status": "planning", "stop_reason": "", "plan": None, "plan_sha": "",
                "approved_at": "", "packages": [], "files": {}, "approvals": [], "verification": [], "proposals": [], "agent_summaries": [],
                "usage": {"input_tokens": 0, "output_tokens": 0}, "events": []}
        ledger = cls(project, task_id, data)
        ledger.save()
        return ledger

    @classmethod
    def load(cls, project, task_id: str) -> "Ledger":
        path = project.agent_dir / "tasks" / task_id / "ledger.json"
        try:
            return cls(project, task_id, json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            raise FileNotFoundError(f"no readable ledger for task '{task_id}'") from exc

    @staticmethod
    def list_ids(project) -> list[str]:
        base = project.agent_dir / "tasks"
        return sorted(p.name for p in base.iterdir() if (p / "ledger.json").is_file()) if base.is_dir() else []

    def save(self) -> None:
        self.data["updated"] = _now()
        with fsutil.file_lock(self.project.lock_dir, f"ledger:{self.id}"):
            fsutil.atomic_write(self.file, (json.dumps(self.data, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))

    def set_status(self, status: str, reason: str = "") -> None:
        self.data["status"], self.data["stop_reason"] = status, reason
        self.event("status", status=status, reason=reason)

    def event(self, kind: str, **info) -> None:
        self.data["events"] = (self.data["events"] + [{"t": _now(), "kind": kind, **info}])[-MAX_EVENTS:]
        self.save()
        if self.listener:
            self.listener({"type": kind, **info})

    def snapshot_original(self, rel: str, content: bytes | None) -> None:
        """Keep the content a file had before the agent first touched it (None = it did not exist), so a diff can be shown later."""
        snaps = self.data.setdefault("snapshots", {})
        if rel in snaps:
            return
        name = None
        if content is not None:
            name = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:16] + ".orig"
            fsutil.atomic_write(self.dir / "snapshots" / name, content)
        snaps[rel] = {"file": name}
        self.save()

    def snapshot_alias(self, new_rel: str, old_rel: str) -> None:
        """After a rename the new path's original is the old path's original."""
        snaps = self.data.setdefault("snapshots", {})
        if old_rel in snaps and new_rel not in snaps:
            snaps[new_rel] = {**snaps[old_rel], "from": old_rel}
            self.save()

    def original(self, rel: str):
        """(known, bytes-or-None): the content before the agent changed `rel`."""
        snap = self.data.get("snapshots", {}).get(rel)
        if snap is None:
            return False, None
        return True, ((self.dir / "snapshots" / snap["file"]).read_bytes() if snap["file"] else None)

    def add_usage(self, usage: dict) -> None:
        for key in ("input_tokens", "output_tokens"):
            self.data["usage"][key] += int(usage.get(key) or 0)

    def record_file(self, rel: str, state: str, sha_before, sha_now, package: str = "", detail: str = "") -> None:
        """Per-file state. A later no-op, failed, conflicting or rolled-back attempt never hides an earlier real write: the file stays `written`
        (its content is still the earlier write) and the attempt is noted in `detail`, so checks keep running on it."""
        old = self.data["files"].get(rel)
        if old and old["state"] == "written" and state in ("unchanged", "rolled_back", "conflict", "failed"):
            self.data["files"][rel] = {**old, "sha_now": sha_now, "detail": f"last edit attempt: {state}" + (f" ({detail})" if detail else "")}
        else:
            keep = old["sha_before"] if old and old["state"] == "written" and state == "written" else sha_before   # sha_before = original content
            self.data["files"][rel] = {"state": state, "sha_before": keep, "sha_now": sha_now, "package": package, "detail": detail}
        self.save()

    def record_approval(self, kind: str, key: str, ok: bool, message: str) -> None:
        self.data["approvals"].append({"t": _now(), "kind": kind, "key": key, "approved": ok, "message": message[:300]})
        self.save()

    def approved_keys(self) -> set[str]:
        return {a["key"] for a in self.data["approvals"] if a["approved"]}

    def add_proposal(self, rel: str, text: str) -> None:
        self.data["proposals"].append({"path": rel, "text": text})
        self.save()

    def add_verification(self, label: str, results: list[dict]) -> None:
        self.data["verification"].append({"t": _now(), "label": label, "results": results})
        self.save()

    def changed_files(self, package: str | None = None) -> list[str]:
        """Files currently in the written state (optionally only those last written by one package); these are what the checks run on."""
        return sorted(p for p, f in self.data["files"].items() if f["state"] in ("written", "rollback_failed") and (package is None or f["package"] == package))

    def brief(self, package_id: str, limit: int = 6000) -> str:
        """Everything a fresh package needs to start: goal, plan, this package, short summaries of finished packages, files touched so far."""
        d, plan = self.data, self.data["plan"]
        lines = [f"TASK LEDGER {self.id}", f"Goal: {d['goal']}", f"Plan: {plan['summary']}", "Steps: " + "; ".join(f"{s['id']} {s['title']}" for s in plan["steps"])]
        for p in d["packages"]:
            mark = {"done": "DONE", "pending": "todo"}.get(p["status"], p["status"])
            lines.append(f"[{mark}] {p['id']} {p['title']} (steps {', '.join(p['steps'])}; files {', '.join(p['files'][:8])})" + (f" - {p['summary']}" if p["summary"] else ""))
        touched = [f"{p} ({f['state']})" for p, f in d["files"].items()]
        if touched:
            lines.append("Files touched so far: " + ", ".join(touched[:40]))
        if d["proposals"]:
            lines.append("Proposals pending the owner: " + ", ".join(p["path"] for p in d["proposals"]))
        lines.append(f"CURRENT PACKAGE: {package_id}")
        return "\n".join(lines)[:limit]
