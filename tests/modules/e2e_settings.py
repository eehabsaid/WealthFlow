"""E2E precondition pinning: AppSettings rows are set / cleared in the DISPOSABLE database only.

The runner copies the developer's real db.sqlite3, so a step must never rely on a setting it did not set itself
(a local `ai_direct_answers=false` once made three AI steps fail). Refuses to touch db.sqlite3. AppSettings has no
cache, so the running test server sees every change immediately.

    with pinned({"ai_direct_answers": "true"}):      # set, run, restore the original rows
        ...
    with fresh_state(["ai_direct_answers"]):         # rows deleted: the stored DEFAULT is what the step sees
        ...
"""

import os
import sqlite3
from contextlib import contextmanager

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _db_path() -> str:
    name = os.environ.get("WEALTHFLOW_DB_NAME", "")
    if not name or name == "db.sqlite3":
        raise RuntimeError("E2E setting pinning refuses to run without a disposable WEALTHFLOW_DB_NAME")
    return os.path.join(ROOT, name)


# What every AI step needs to reach the chat at all (a fresh DB has no provider, so the endpoint answers "AI disabled"
# before the instant engine runs). Nothing here needs a reachable model: instant answers and file export use 0 LLM calls.
AI_ENGINE_PINS = {"ai_enabled": "true", "ai_provider": "ollama", "ai_investigator_mode": "auto", "ai_file_generation": "true",
                  "ai_file_max_mb": "10", "ai_file_max_rows": "50000"}


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(_db_path(), timeout=15)


def snapshot(keys) -> list[tuple]:
    marks = ",".join("?" * len(keys))
    with _connect() as db:
        return db.execute(f"SELECT key, value, owner_id FROM core_appsettings WHERE key IN ({marks})", list(keys)).fetchall()


def clear(keys) -> None:
    marks = ",".join("?" * len(keys))
    with _connect() as db:
        db.execute(f"DELETE FROM core_appsettings WHERE key IN ({marks})", list(keys))


def restore(keys, rows) -> None:
    clear(keys)
    with _connect() as db:
        db.executemany("INSERT INTO core_appsettings (key, value, description, owner_id) VALUES (?, ?, '', ?)", rows)


@contextmanager
def fresh_state(keys):
    """Delete every row (global and per-user) of `keys`, restore the originals afterwards."""
    keys, saved = list(keys), snapshot(keys)
    clear(keys)
    try:
        yield
    finally:
        restore(keys, saved)


@contextmanager
def pinned(values: dict):
    """Set each key as a global row (per-user rows removed so the pin is what every user resolves)."""
    keys, saved = list(values), snapshot(list(values))
    clear(keys)
    with _connect() as db:
        db.executemany("INSERT INTO core_appsettings (key, value, description, owner_id) VALUES (?, ?, '', NULL)", list(values.items()))
    try:
        yield
    finally:
        restore(keys, saved)


def rows(sql: str, params: tuple = ()) -> list[tuple]:
    """Read-only query on the disposable DB (what the test server wrote)."""
    with _connect() as db:
        return db.execute(sql, params).fetchall()


def django_exec(code: str) -> str:
    """Run a Django shell snippet against the disposable DB (ORM access for fixtures the API cannot create)."""
    import subprocess
    import sys

    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "wealthflow.settings"}
    done = subprocess.run([sys.executable, "manage.py", "shell", "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    if done.returncode:
        raise RuntimeError(done.stderr[-400:])
    return done.stdout.strip()
