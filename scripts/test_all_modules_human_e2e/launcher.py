"""One-command runner for the human-QA modules script (same idea as scripts/run_full_e2e.py).

`python scripts/test_all_modules_human_e2e/__init__.py` calls this when it is started by hand: it copies db.sqlite3 to a
disposable database, migrates + seeds it, starts the dev server on a free port, runs the 5 phases against it, stops the
server, deletes the copy and checks that db.sqlite3 was not touched. Nothing to set up by hand.
"""

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))

from e2e_process_utils import choose_port, err, files_identical, log, wait_for_server  # noqa: E402

CHILD_FLAG = "WEALTHFLOW_HUMAN_E2E_CHILD"
HOST = os.environ.get("WEALTHFLOW_E2E_HOST", "127.0.0.1")
ADMIN = ("eehab_said", "Eehabdev1")   # the user scripts/e2e_seed.py creates in the disposable database


def _stop(proc):
    if proc is not None and proc.poll() is None:
        log(f"Stopping test server (pid {proc.pid})")
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def _remove(path):
    """Delete a file; on Windows the stopped server can still hold it for a moment, so retry and never crash the clean-up."""
    for _ in range(10):
        try:
            if os.path.exists(path):
                os.remove(path)
            return True
        except OSError:
            time.sleep(1)
    err(f"Could not delete {os.path.basename(path)} (still in use) - delete it by hand.")
    return False


def run() -> int:
    prod_db = os.path.join(_REPO_ROOT, "db.sqlite3")
    if not os.path.exists(prod_db):
        err("db.sqlite3 not found: nothing to copy for the disposable test database.")
        return 2
    try:
        port = str(choose_port(HOST, os.environ.get("WEALTHFLOW_E2E_PORT", "8000"), "WEALTHFLOW_E2E_PORT" in os.environ))
    except OSError as ex:
        err(f"Requested E2E port is unavailable: {ex}")
        return 2
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup, test_db = os.path.join(_REPO_ROOT, f"db.sqlite3.bak.{stamp}"), os.path.join(_REPO_ROOT, f"db_e2e_human_{stamp}.sqlite3")
    log(f"Backing up db.sqlite3 -> {os.path.basename(backup)}; disposable copy -> {os.path.basename(test_db)}")
    shutil.copy2(prod_db, backup)
    shutil.copy2(prod_db, test_db)

    env = os.environ.copy()
    env.update(WEALTHFLOW_DB_NAME=os.path.basename(test_db), DJANGO_SETTINGS_MODULE="wealthflow.settings", WEALTHFLOW_E2E_HOST=HOST,
               WEALTHFLOW_E2E_PORT=port, WF_USERNAME=env.get("WF_USERNAME") or ADMIN[0], WF_PASSWORD=env.get("WF_PASSWORD") or ADMIN[1],
               PYTHONPATH=_REPO_ROOT + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""))
    server, code, server_log = None, 1, None
    try:
        for cmd in (["manage.py", "migrate", "--noinput"], [os.path.join("scripts", "e2e_seed.py")]):
            if subprocess.run([sys.executable, *cmd], cwd=_REPO_ROOT, env=env).returncode != 0:
                err(f"{cmd[0]} failed on the disposable database - aborting.")
                return 1
        log(f"Starting the dev server on the disposable database, port {port}")
        server_log = open(os.path.join(_REPO_ROOT, f"e2e_server_human_{stamp}.log"), "w")
        server = subprocess.Popen([sys.executable, "manage.py", "runserver", f"{HOST}:{port}", "--noreload"],
                                  cwd=_REPO_ROOT, env=env, stdout=server_log, stderr=subprocess.STDOUT)
        if not wait_for_server(f"http://{HOST}:{port}/accounts/login/", 30) or server.poll() is not None:
            err(f"Server did not start. See {server_log.name}")
            return 1
        env[CHILD_FLAG] = "1"
        code = subprocess.run([sys.executable, os.path.join("scripts", "test_all_modules_human_e2e", "__init__.py")], cwd=_REPO_ROOT, env=env).returncode
    finally:
        _stop(server)
        if server_log:
            server_log.close()
        for suffix in ("", "-wal", "-shm"):
            _remove(test_db + suffix)
        if files_identical(prod_db, backup):
            log("Verified db.sqlite3 is untouched.")
            _remove(backup)
        else:
            err("db.sqlite3 changed during the run - restoring it from the backup.")
            shutil.copy2(backup, prod_db)
        if server_log and code == 0:
            _remove(server_log.name)
    log(f"Human-QA modules finished with exit code {code}.")
    return code
