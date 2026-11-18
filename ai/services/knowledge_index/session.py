"""One entry point for readers: open the index, make sure it is current (cheap stat check, throttled), report how fresh it is."""

from __future__ import annotations

import time

from ai.services.knowledge_index import config, indexer, store

_state = {"checked": 0.0}


def reset_throttle() -> None:
    _state["checked"] = 0.0


def open_fresh(force: bool = False):
    """(connection, info). info = {current, refreshed, error}. Never raises: on a refresh failure the caller still gets the
    existing index plus info['current']=False, and evidence built from it is marked stale if the file really differs."""
    conn = store.connect()
    info = {"current": True, "refreshed": None, "error": None}
    now = time.monotonic()
    if force or now - _state["checked"] >= config.FRESH_CHECK_SECONDS:
        try:
            summary = indexer.refresh(conn)
            _state["checked"] = now
            if summary["added"] or summary["changed"] or summary["deleted"] or summary["renamed"] or summary["rebuilt"]:
                info["refreshed"] = {k: summary[k] for k in ("added", "changed", "deleted", "renamed", "rebuilt")}
        except Exception as exc:   # noqa: BLE001 - reading must keep working on the last good index
            info.update(current=False, error=f"{type(exc).__name__}: {exc}"[:200])
    return conn, info
