"""Blocking approvals: the engine thread asks and waits; a UI answers through the API. Stop (the cancel token) unblocks a waiting request as a denial."""

from __future__ import annotations

import datetime
import threading


class QueueApprover:
    def __init__(self, emit, cancel):
        self.emit, self.cancel = emit, cancel
        self._lock, self._pending, self._seq = threading.Lock(), {}, 0

    def ask(self, kind: str, message: str) -> bool:
        with self._lock:
            self._seq += 1
            aid = f"a{self._seq}"
            entry = {"id": aid, "kind": kind, "message": message, "created": datetime.datetime.now().isoformat(timespec="seconds"),
                     "_event": threading.Event(), "_answer": None}
            self._pending[aid] = entry
        self.emit({"type": "approval_request", "id": aid, "kind": kind, "message": message[:1500]})
        while not entry["_event"].wait(0.2):
            if self.cancel.is_set():
                break
        with self._lock:
            self._pending.pop(aid, None)
        ok = entry["_answer"] is True and not self.cancel.is_set()
        self.emit({"type": "approval_result", "id": aid, "approved": ok})
        return ok

    def answer(self, aid: str, approve: bool) -> bool:
        with self._lock:
            entry = self._pending.get(aid)
            if not entry or entry["_answer"] is not None:   # unknown, or already answered: the first answer wins (two UIs may both be open)
                return False
            entry["_answer"] = bool(approve)
            entry["_event"].set()
            return True

    def pending(self) -> list[dict]:
        with self._lock:
            return [{k: v for k, v in e.items() if not k.startswith("_")} for e in self._pending.values()]
