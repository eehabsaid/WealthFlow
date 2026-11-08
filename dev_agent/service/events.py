"""Per-task event log: every event gets a sequence number, is appended to tasks/<id>/events.jsonl and can be streamed or fetched `after` a number.
This file is the one protocol the web UI and the VS Code extension both read."""

from __future__ import annotations

import datetime
import json
import threading
from pathlib import Path

MAX_FIELD = 2000


def _clip(value):
    if isinstance(value, str):
        return value if len(value) <= MAX_FIELD else value[:MAX_FIELD] + "..."
    if isinstance(value, dict):
        return {k: _clip(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clip(v) for v in value[:100]]
    return value


class EventLog:
    def __init__(self, path):
        self.path, self.closed = Path(path), False
        self._events: list[dict] = []
        self._cond = threading.Condition()
        self._repair = False
        try:
            text = self.path.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                try:
                    self._events.append(json.loads(line))
                except ValueError:
                    continue   # a torn last line after a crash
            self._repair = bool(text) and not text.endswith("\n")   # the torn line has no newline: the next event must not be glued onto it
        except OSError:
            pass

    def append(self, event: dict) -> dict:
        with self._cond:
            rec = {"seq": len(self._events) + 1, "t": datetime.datetime.now().isoformat(timespec="seconds"), **_clip(event)}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(("\n" if self._repair else "") + json.dumps(rec, ensure_ascii=False) + "\n")
            self._repair = False
            self._events.append(rec)
            self._cond.notify_all()
        return rec

    def after(self, seq: int, limit: int = 500) -> list[dict]:
        with self._cond:
            return self._events[max(0, seq): max(0, seq) + limit]

    def wait(self, seq: int, timeout: float) -> list[dict]:
        """Events after `seq`; blocks up to `timeout` seconds when there are none yet."""
        with self._cond:
            if len(self._events) <= seq and not self.closed:
                self._cond.wait(timeout)
            return self._events[max(0, seq): max(0, seq) + 500]

    def last_seq(self) -> int:
        with self._cond:
            return len(self._events)

    def close(self) -> None:
        with self._cond:
            self.closed = True
            self._cond.notify_all()
