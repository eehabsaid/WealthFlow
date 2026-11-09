"""One run per task. A lock file coding_agent/tasks/<id>/run.lock holds the process id of whoever is planning or executing the task, so a second
process (CLI, server, another editor window) cannot run the same task at the same time, and a crash is recognised later: a lock whose process
is gone is stale and means the run was interrupted."""

from __future__ import annotations

import contextlib
import json
import os
import time

from ai.dev_agent.tools import proctree


class TaskBusy(RuntimeError):
    pass


def _path(ledger):
    return ledger.dir / "run.lock"


def holder(ledger) -> int | None:
    """Process id that is running this task right now, or None (no lock, or a stale lock left by a crashed process)."""
    try:
        pid = int(json.loads(_path(ledger).read_text(encoding="utf-8"))["pid"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return pid if pid == os.getpid() or proctree.pid_alive(pid) else None


def acquire(ledger) -> None:
    ledger.dir.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(_path(ledger), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            pid = holder(ledger)
            if pid is not None and pid != os.getpid():
                raise TaskBusy(f"task {ledger.id} is already running in another process (pid {pid})") from None
            with contextlib.suppress(OSError):   # stale (crashed) or our own leftover: take it over
                _path(ledger).unlink()
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "started": time.time()}, handle)
        return
    raise TaskBusy(f"could not lock task {ledger.id}")


def release(ledger) -> None:
    with contextlib.suppress(OSError):
        _path(ledger).unlink()


@contextlib.contextmanager
def hold(ledger):
    acquire(ledger)
    try:
        yield
    finally:
        release(ledger)

