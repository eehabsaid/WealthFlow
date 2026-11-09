"""Crash / resume recovery. A task whose status says it is planning or executing but whose process is gone was interrupted (crash, power loss,
killed editor). `recover` turns it into a normal `stopped` task and makes its ledger match the disk, so `execute`/Resume continues it:
finished packages are never repeated, and files a half-finished package already wrote are reported exactly as they are on disk."""

from __future__ import annotations

import os

from ai.dev_agent.core import fsutil
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.engine import runlock

LIVE = ("planning", "approved", "executing")
NOTE = ("NOTE: this package was interrupted earlier (crash or kill). Files it already wrote are listed above as touched. Read them first, "
        "continue from there and do not redo finished work.")


def _disk(project, rel: str):
    try:
        return fsutil.read_bytes(project.root / rel)
    except OSError:
        return None


def reconcile(ledger) -> list[str]:
    """Make the per-file states match the disk. Returns one line per correction (empty when everything already matched)."""
    d, notes, project = ledger.data, [], ledger.project
    for rel, snap in sorted(d.get("snapshots", {}).items()):
        if rel in d["files"] or snap.get("from"):
            continue   # recorded already (checked below), or a rename target
        _, original = ledger.original(rel)
        now = _disk(project, rel)
        if now == original:
            continue   # the write never happened (or was rolled back)
        pkg = next((p["id"] for p in d["packages"] if p["status"] in ("running", "stopped") and rel in p["files"]), "")
        state = "deleted" if now is None else "written"
        ledger.record_file(rel, state, fsutil.sha(original) if original is not None else None, fsutil.sha(now) if now is not None else None, pkg,
                           "recovered after an interruption: the write may have been partial, checks will run on it")
        notes.append(f"{rel}: found {state} on disk but missing in the ledger")
    for rel, entry in sorted(d["files"].items()):
        if entry["state"] != "written":
            continue
        now = _disk(project, rel)
        digest = fsutil.sha(now) if now is not None else None
        if digest != entry.get("sha_now"):
            ledger.data["files"][rel] = {**entry, "sha_now": digest, "detail": "changed on disk after the last recorded write (interruption or outside edit)"}
            ledger.save()
            notes.append(f"{rel}: content on disk differs from the last recorded write")
    return notes


def recover_task(ledger) -> str:
    """'' when nothing was needed, otherwise the reason text the task now carries."""
    d = ledger.data
    if d["status"] not in LIVE or runlock.holder(ledger) not in (None, os.getpid()):
        return ""   # not running at all, or another live process is working on it
    notes = reconcile(ledger)
    for pkg in d["packages"]:
        if pkg["status"] == "running":
            pkg["status"] = "interrupted"
    resumable = bool(d["plan"] and d["approved_at"])
    reason = ("interrupted: the agent process ended unexpectedly while the task was " + ("running; Resume continues it" if resumable
              else "being planned; start the task again"))
    if notes:
        reason += " (" + "; ".join(notes[:5]) + ")"
    ledger.set_status("stopped", reason)
    if runlock.holder(ledger) is None:
        runlock.release(ledger)   # drop a stale lock file (never our own: the run in progress needs it)
    return reason


def recover(project) -> list[tuple[str, str]]:
    """Check every task of the project. [(task id, reason)] for the ones that were interrupted."""
    out = []
    for task_id in Ledger.list_ids(project):
        try:
            ledger = Ledger.load(project, task_id)
            reason = recover_task(ledger)
        except (FileNotFoundError, OSError, KeyError):
            continue   # an unreadable ledger is left alone; it is not ours to guess about
        if reason:
            out.append((task_id, reason))
    return out
