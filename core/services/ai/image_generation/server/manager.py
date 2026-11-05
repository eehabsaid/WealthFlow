"""Lifecycle of the managed image server: start on demand, wait until it answers, never start a second copy, stop cleanly.

Provider-independent: the provider passes its start command, its API URL and a `probe()` that says whether the server answers.
A server that already answers (started by anything else) is used as it is and is never stopped by WealthFlow."""

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
_child = None              # the Popen this Django process started (None: started elsewhere or not started)
_atexit_registered = False


def _wait_ready(probe, timeout: float, pid: int) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if probe():
            return
        if (_child is not None and _child.pid == pid and _child.poll() is not None) or not state.pid_alive(pid):
            code = _child.poll() if _child is not None and _child.pid == pid else None
            state.clear_state()
            tail = state.log_tail()
            raise ServerError("The image server stopped while starting" + (f" (exit code {code})" if code is not None else "")
                              + (f": {tail}" if tail else ". See runtime/image_server/server.log."))
        time.sleep(1)
    raise ServerError(f"The image server is still starting after {int(timeout)} seconds; try again in a moment."
                      + (f" Last output: {state.log_tail(4, 300)}" if state.log_tail(4, 300) else ""))


def ensure_running(command: str, endpoint: str, probe, timeout: float = READY_TIMEOUT_S) -> str:
    """Make sure the server answers; returns a short status text. Raises ServerError when it cannot be brought up."""
    global _child, _atexit_registered
    if probe():
        saved = state.read_state()
        return "Image server is running" + (f" (started by WealthFlow, pid {saved['pid']})" if saved and state.is_same_process(saved) else "")
    args = process.build_args(command, endpoint)
    process.check_executable(args)
    with _lock, state.file_lock(timeout):
        if probe():                                  # another worker finished starting it while we waited for the lock
            return "Image server is running"
        saved = state.read_state()
        if saved and state.is_same_process(saved):   # started earlier and still loading: wait for it, do not start another
            _wait_ready(probe, timeout, saved["pid"])
            return f"Image server is running (started by WealthFlow, pid {saved['pid']})"
        state.clear_state()
        child = process.spawn(args)
        _child = child
        state.write_state({"pid": child.pid, "start_time": state.start_time(child.pid), "command": " ".join(args)[:400], "endpoint": endpoint})
        if not _atexit_registered:
            atexit.register(stop_own_server)
            _atexit_registered = True
        logger.info("Image server started (pid %s)", child.pid)
        _wait_ready(probe, timeout, child.pid)
        return f"Image server started by WealthFlow (pid {child.pid})"


def stop_server() -> bool:
    """Stop the server WealthFlow started (this process's child, or a verified earlier one). Anything else is left alone."""
    global _child
    with _lock:
        saved = state.read_state()
        pid = _child.pid if _child is not None and _child.poll() is None else (saved["pid"] if saved and state.is_same_process(saved) else None)
        if pid is None:
            state.clear_state()
            _child = None
            return False
        state.kill_tree(pid, force=state.IS_WINDOWS)   # a windowless console process ignores the polite request; nothing to flush
        deadline = time.monotonic() + STOP_WAIT_S
        while time.monotonic() < deadline and ((_child is not None and _child.poll() is None) or (_child is None and state.pid_alive(pid))):
            time.sleep(0.2)
        if (_child is not None and _child.poll() is None) or (_child is None and state.pid_alive(pid)):
            state.kill_tree(pid, force=True)
        if _child is not None:
            try:
                _child.wait(timeout=STOP_WAIT_S)
            except Exception:
                logger.warning("Image server pid %s did not exit", pid)
        _child = None
        state.clear_state()
        logger.info("Image server stopped (pid %s)", pid)
        return True


def stop_own_server() -> None:
    """At interpreter exit: stop only a server this very process started."""
    if _child is not None:
        stop_server()


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
