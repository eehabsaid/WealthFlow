"""Lifecycle of the managed image server: start on demand, wait until it answers, never start a second copy, stop cleanly.

Provider-independent: the provider passes its start command, its API URL and a `probe()` that says whether the server answers.
Servers are told apart by API URL (state.endpoint_key). A server that already answers (started by anything else) is used as it
is and is never stopped by WealthFlow."""

from __future__ import annotations

import atexit
import logging
import threading
import time

from . import process, state
from .errors import ServerError

logger = logging.getLogger(__name__)

READY_TIMEOUT_S = 300      # the first start loads large models
STOP_WAIT_S = 10
_lock = threading.Lock()
_children: dict = {}       # key -> the Popen this Django process started (absent: started elsewhere or not started)
_atexit_registered = False


def _mine(key: str, pid: int):
    child = _children.get(key)
    return child if child is not None and child.pid == pid else None


def _wait_ready(probe, timeout: float, pid: int, key: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if probe():
            return
        child = _mine(key, pid)
        if (child is not None and child.poll() is not None) or not state.pid_alive(pid):
            code = child.poll() if child is not None else None
            state.clear_state(key)
            tail = state.log_tail(key)
            raise ServerError("The image server stopped while starting" + (f" (exit code {code})" if code is not None else "")
                              + (f": {tail}" if tail else f". See runtime/image_server/server-{key}.log."))
        time.sleep(1)
    tail = state.log_tail(key, 4, 300)
    raise ServerError(f"The image server is still starting after {int(timeout)} seconds; try again in a moment."
                      + (f" Last output: {tail}" if tail else ""))


def ensure_running(command: str, endpoint: str, probe, timeout: float = READY_TIMEOUT_S) -> str:
    """Make sure the server at `endpoint` answers; returns a short status text. Raises ServerError when it cannot be brought up."""
    global _atexit_registered
    key = state.endpoint_key(endpoint)
    if probe():
        saved = state.read_state(key)
        return "Image server is running" + (f" (started by WealthFlow, pid {saved['pid']})" if saved and state.is_same_process(saved) else "")
    args = process.build_args(command, endpoint)
    process.check_executable(args)
    with _lock, state.file_lock(key, timeout):
        if probe():                                  # another worker finished starting it while we waited for the lock
            return "Image server is running"
        saved = state.read_state(key)
        if saved and state.is_same_process(saved):   # this endpoint's server was started earlier and is still loading
            _wait_ready(probe, timeout, saved["pid"], key)
            return f"Image server is running (started by WealthFlow, pid {saved['pid']})"
        state.clear_state(key)
        child = process.spawn(args, key)
        _children[key] = child
        state.write_state(key, {"pid": child.pid, "start_time": state.start_time(child.pid), "command": " ".join(args)[:400], "endpoint": endpoint})
        if not _atexit_registered:
            atexit.register(stop_own_servers)
            _atexit_registered = True
        logger.info("Image server started (pid %s, %s)", child.pid, key)
        _wait_ready(probe, timeout, child.pid, key)
        return f"Image server started by WealthFlow (pid {child.pid})"


def stop_server(endpoint: str) -> bool:
    """Stop the server at `endpoint` if WealthFlow started it (this process's child, or a verified earlier one).
    Anything else, including another endpoint's server, is left alone."""
    key = state.endpoint_key(endpoint)
    with _lock:
        saved = state.read_state(key)
        child = _children.get(key)
        pid = child.pid if child is not None and child.poll() is None else (saved["pid"] if saved and state.is_same_process(saved) else None)
        if pid is None:
            state.clear_state(key)
            _children.pop(key, None)
            return False
        state.kill_tree(pid, force=state.IS_WINDOWS)   # a windowless console process ignores the polite request; nothing to flush
        alive = (lambda: child.poll() is None) if child is not None and child.pid == pid else (lambda: state.pid_alive(pid))
        deadline = time.monotonic() + STOP_WAIT_S
        while time.monotonic() < deadline and alive():
            time.sleep(0.2)
        if alive():
            state.kill_tree(pid, force=True)
        if child is not None and child.pid == pid:
            try:
                child.wait(timeout=STOP_WAIT_S)
            except Exception:
                logger.warning("Image server pid %s did not exit", pid)
        _children.pop(key, None)
        state.clear_state(key)
        logger.info("Image server stopped (pid %s, %s)", pid, key)
        return True


def stop_own_servers() -> None:
    """At interpreter exit: stop only the servers this very process started."""
    for key, child in list(_children.items()):
        if child.poll() is None:
            saved = state.read_state(key)
            stop_server(saved["endpoint"] if saved else "")


_warming = threading.Event()


def warm_start(command: str, endpoint: str, probe) -> None:
    """Start in the background (settings saved / workspace opened) so the first image does not wait for the server.
    One warm start at a time: repeated calls while one is running do nothing."""
    if _warming.is_set():
        return
    _warming.set()

    def run():
        try:
            ensure_running(command, endpoint, probe)
        except ServerError as exc:
            logger.warning("Image server warm start failed: %s", exc)
        except Exception:
            logger.exception("Image server warm start crashed")
        finally:
            _warming.clear()
    threading.Thread(target=run, name="image-server-warm-start", daemon=True).start()
