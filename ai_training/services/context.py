"""Switches recording on for the code that runs inside it (the training runner), without touching global settings."""

from __future__ import annotations

import contextvars
from contextlib import contextmanager

_ACTIVE: contextvars.ContextVar[dict | None] = contextvars.ContextVar("agent_trace_context", default=None)


@contextmanager
def collecting(*, case_key: str = "", attempt: int = 1, expected=None, source: str = "generated"):
    token = _ACTIVE.set({"case_key": case_key, "attempt": attempt, "expected": expected, "source": source, "saved": []})
    try:
        yield _ACTIVE.get()
    finally:
        _ACTIVE.reset(token)


def current() -> dict | None:
    return _ACTIVE.get()
