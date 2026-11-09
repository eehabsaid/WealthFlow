"""Cancellation shared by the CLI, the web UI and the VS Code extension: one token per run. Setting it stops the model loop between steps,
aborts a model request that is waiting on the network, and kills a running command's whole process tree."""

from __future__ import annotations

import threading


class Cancelled(Exception):
    pass


class CancelToken:
    def __init__(self):
        self._event, self._lock, self._callbacks, self.reason = threading.Event(), threading.Lock(), [], ""

    def set(self, reason: str = "stopped by user") -> None:
        with self._lock:
            if self._event.is_set():
                return
            self.reason = reason
            self._event.set()
            callbacks, self._callbacks = self._callbacks, []
        for callback in callbacks:
            try:
                callback()
            except Exception:   # one failing callback must not stop the others (e.g. a process that already exited)
                pass

    def is_set(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout: float) -> bool:
        return self._event.wait(timeout)

    def check(self) -> None:
        if self._event.is_set():
            raise Cancelled(self.reason)

    def on_cancel(self, callback):
        """Run `callback` when cancelled (at once if it already is). Returns a function that removes the callback again."""
        with self._lock:
            if not self._event.is_set():
                self._callbacks.append(callback)
                return lambda: self._remove(callback)
        callback()
        return lambda: None

    def _remove(self, callback) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
