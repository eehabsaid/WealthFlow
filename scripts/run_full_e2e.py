#!/usr/bin/env python3
"""
run_full_e2e.py — the ONE command to run WealthFlow's full human-QA E2E
suite safely, end to end, on any OS (Windows/macOS/Linux — no bash needed).

WHAT THIS FIXES vs. the previous setup
---------------------------------------
1. scripts/test_ui_human_full_e2e.py (the suite that actually covers every
   module/page/tab/CRUD flow) was running directly against the real
   db.sqlite3, relying only on backup+restore around it. This script now
   makes that suite run against a disposable COPY instead — production is
   never opened by the app process at all, matching the same safe pattern
   already used by scripts/run_e2e_tests.sh's pytest path.
2. tests/modules/*.py (14 module test files) were never actually wired
   into anything pytest could discover. They ARE correctly wired into
   scripts/test_ui_human_full_e2e.py already (that script imports and
   calls each one directly, not via pytest) — this wrapper is what makes
   that comprehensive suite the thing that actually gets run, safely.
3. One command instead of several manual steps (copy db, migrate, start
   server, wait, run suite, stop server, verify/restore, clean up).

USAGE
-----
    python scripts/run_full_e2e.py
    python scripts/run_full_e2e.py --mode=smoke
    python scripts/run_full_e2e.py --mode=module --module=fixed_assets
    python scripts/run_full_e2e.py --headed --slowmo=250

Any arguments not listed below are passed straight through to
scripts/test_ui_human_full_e2e.py (--mode, --module, --page, --lang,
--theme, --device, --headed, --headless, --slowmo, --screenshots).

SAFETY GUARANTEE
-----------------
- db.sqlite3 is backed up before anything else runs.
- The Django server this script starts is pointed at a disposable COPY via
  the WEALTHFLOW_DB_NAME env var — the real db.sqlite3 is never opened by
  the app during the run.
- On ANY outcome (pass, fail, or crash of this wrapper itself), db.sqlite3
  is diffed against its pre-run backup and restored automatically if it
  changed — this is a redundant safety net on top of #2, not the primary
  mechanism, since #2 already means it shouldn't change at all.
- The disposable copy and its WAL/SHM sidecars are deleted on exit.
- Exit code mirrors the underlying suite's exit code (0 = clean pass).
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD_DB = os.path.join(ROOT_DIR, "db.sqlite3")
SERVER_HOST = os.environ.get("WEALTHFLOW_E2E_HOST", "127.0.0.1")
SERVER_PORT = os.environ.get("WEALTHFLOW_E2E_PORT", "8000")
READY_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/accounts/login/"
READY_TIMEOUT_SECONDS = 30


def log(msg: str) -> None:
    print(f"[e2e] {msg}", flush=True)


def err(msg: str) -> None:
    print(f"[e2e][ERROR] {msg}", file=sys.stderr, flush=True)


def files_identical(a: str, b: str) -> bool:
    if not (os.path.exists(a) and os.path.exists(b)):
        return False
    if os.path.getsize(a) != os.path.getsize(b):
        return False
    with open(a, "rb") as fa, open(b, "rb") as fb:
        while True:
            chunk_a = fa.read(1024 * 1024)
            chunk_b = fb.read(1024 * 1024)
            if chunk_a != chunk_b:
                return False
            if not chunk_a:
                return True


def wait_for_server(url: str, timeout_seconds: int) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status < 500:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(1)
    return False


def _install_signal_handlers() -> None:
    def _handle(signum, frame):
        raise KeyboardInterrupt(f"received signal {signum}")

    signal.signal(signal.SIGTERM, _handle)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _handle)


def main() -> int:
    _install_signal_handlers()

    if not os.path.exists(PROD_DB):
        err(f"{PROD_DB} not found — are you running this from the repo root?")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_db = os.path.join(ROOT_DIR, f"db.sqlite3.bak.{timestamp}")
    test_db = os.path.join(ROOT_DIR, f"db_e2e_test_{timestamp}.sqlite3")

    log(f"Backing up production database -> {os.path.basename(backup_db)}")
    shutil.copy2(PROD_DB, backup_db)

    log(f"Creating disposable test database (copy of production data) -> {os.path.basename(test_db)}")
    shutil.copy2(PROD_DB, test_db)

    env = os.environ.copy()
    env["WEALTHFLOW_DB_NAME"] = os.path.basename(test_db)
    env["DJANGO_SETTINGS_MODULE"] = "wealthflow.settings"
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = ROOT_DIR + (os.pathsep + existing_pythonpath if existing_pythonpath else "")

    server_proc = None
    suite_exit_code = 1

    try:
        log("Applying any pending migrations to the TEST database only (production is never migrated)")
        migrate_result = subprocess.run(
            [sys.executable, "manage.py", "migrate", "--noinput"],
            cwd=ROOT_DIR, env=env,
        )
        if migrate_result.returncode != 0:
            err("Migration against the disposable copy failed — aborting before starting the server.")
            return migrate_result.returncode

        log(f"Starting Django dev server against the TEST database on {SERVER_HOST}:{SERVER_PORT}")
        server_log_path = os.path.join(ROOT_DIR, f"e2e_server_{timestamp}.log")
        server_log = open(server_log_path, "w")
        server_proc = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", f"{SERVER_HOST}:{SERVER_PORT}", "--noreload"],
            cwd=ROOT_DIR, env=env, stdout=server_log, stderr=subprocess.STDOUT,
        )

        log("Waiting for the server to become ready...")
        if not wait_for_server(READY_URL, READY_TIMEOUT_SECONDS):
            err(f"Server did not become ready within {READY_TIMEOUT_SECONDS}s. See {server_log_path}")
            return 1
        log("Server is up.")

        log("Running the full human-QA E2E suite against the TEST database...")
        suite_args = sys.argv[1:]
        suite_result = subprocess.run(
            [sys.executable, os.path.join("scripts", "test_ui_human_full_e2e.py"), *suite_args],
            cwd=ROOT_DIR, env=env,
        )
        suite_exit_code = suite_result.returncode

    finally:
        if server_proc is not None and server_proc.poll() is None:
            log(f"Stopping test server (pid {server_proc.pid})")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_proc.kill()
                server_proc.wait()

        for suffix in ("", "-wal", "-shm"):
            path = test_db + suffix
            if os.path.exists(path):
                os.remove(path)
        log(f"Removed disposable test database ({os.path.basename(test_db)})")

        if os.path.exists(PROD_DB) and os.path.exists(backup_db):
            if not files_identical(PROD_DB, backup_db):
                err("Production database changed during the test run — restoring from backup automatically.")
                shutil.copy2(backup_db, PROD_DB)
            else:
                log("Verified production database is untouched.")

        log(f"Production db backup kept at: {os.path.basename(backup_db)}")

    log(f"Suite finished with exit code {suite_exit_code}.")
    return suite_exit_code


if __name__ == "__main__":
    sys.exit(main())
