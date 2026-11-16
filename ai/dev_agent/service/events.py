"""Per-task event log: every event gets a sequence number, is appended to tasks/<id>/events.jsonl and can be streamed or fetched `after` a number.
This file is the one protocol the web UI and the VS Code extension both read."""

from __future__ import annotations

import datetime
import json
import threading
from pathlib import Path

MAX_FIELD = 2000
TRACE = "trace"   # full-trajectory events (engine/trace.py): written to the file and kept for training export, never sent to the live UI feed


def _clip(value):
    if isinstance(value, str):
        return value if len(value) <= MAX_FIELD else value[:MAX_FIELD] + "..."
    if isinstance(value, dict):
        return {k: _clip(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clip(v) for v in value[:100]]
    return value


class EventLog:
    """Public events (numbered `seq` 1, 2, 3 ... without gaps) are what the UIs read. Trace events (full trajectory, see engine/trace.py) go into the
    same file in order but carry their own `tseq` and are never part of the live feed."""

    def __init__(self, path):
        self.path, self.closed = Path(path), False
        self._events: list[dict] = []   # everything, in file order
        self._public: list[dict] = []   # index = seq - 1
        self._cond = threading.Condition()
        self._repair = False
        try:
            text = self.path.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                try:
                    self._keep(json.loads(line))
                except ValueError:
                    continue   # a torn last line after a crash
            self._repair = bool(text) and not text.endswith("\n")   # the torn line has no newline: the next event must not be glued onto it
        except OSError:
            pass

    def _keep(self, rec: dict) -> None:
        self._events.append(rec)
        if rec.get("type") != TRACE:
            self._public.append(rec)

    def append(self, event: dict) -> dict:
        with self._cond:
            stamp = datetime.datetime.now().isoformat(timespec="seconds")
            if event.get("type") == TRACE:   # already capped and redacted by the tracer
                rec = {"tseq": len(self._events) - len(self._public) + 1, "t": stamp, **event}
            else:
                rec = {"seq": len(self._public) + 1, "t": stamp, **_clip(event)}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(("\n" if self._repair else "") + json.dumps(rec, ensure_ascii=False) + "\n")
            self._repair = False
            self._keep(rec)
            if rec.get("type") != TRACE:
                self._cond.notify_all()
        return rec

    def after(self, seq: int, limit: int = 500) -> list[dict]:
        with self._cond:
            return self._public[max(0, seq): max(0, seq) + limit]

    def wait(self, seq: int, timeout: float) -> list[dict]:
        """Events after `seq`; blocks up to `timeout` seconds when there are none yet."""
        with self._cond:
            if len(self._public) <= seq and not self.closed:
                self._cond.wait(timeout)
            return self._public[max(0, seq): max(0, seq) + 500]

    def all_events(self) -> list[dict]:
        """Everything, trace events included (training export, tests)."""
        with self._cond:
            return list(self._events)

    def last_seq(self) -> int:
        with self._cond:
            return len(self._public)

    def close(self) -> None:
        with self._cond:
            self.closed = True
            self._cond.notify_all()
