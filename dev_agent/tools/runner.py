"""Run one command as an argv list (never through a shell), with a timeout, a clean environment and the whole process tree killed on timeout.
Works on Windows 11 (.cmd/.bat shims such as npx and eslint are resolved with PATHEXT and their arguments checked) and POSIX."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time

from ..engine.budget import clip_log
from . import proctree

MAX_CAPTURE = 4_000_000   # keep at most this much output in memory; the rest is read and dropped
BATCH_UNSAFE = set('&|<>^%"\n\r')
DROP_ENV = ("GIT_EXTERNAL_DIFF", "GIT_PAGER", "PAGER", "GIT_ASKPASS", "GIT_SSH_COMMAND", "GIT_EDITOR", "EDITOR")


def _env() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in DROP_ENV}
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "GIT_PAGER": "cat", "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "NO_COLOR": "1"})
    return env


def resolve_exe(argv0: str) -> str | None:
    """`python` (and python3, py, python3.12) means the interpreter running the agent, so the project's own venv is used."""
    from ..guard.commands import exe_name
    if not any(sep in argv0 for sep in "/\\") and exe_name(argv0) == "python":
        return sys.executable
    return shutil.which(argv0)


def run(argv: list[str], cwd, timeout: int, max_chars: int = 6000, cancel=None) -> dict:
    """status: PASSED | FAILED | CANCELLED (Stop was pressed) | NOT RUN. On timeout or Stop the whole process tree is killed."""
    exe = resolve_exe(argv[0])
    if not exe:
        return {"status": "NOT RUN", "exit_code": None, "output": f"executable not found: {argv[0]}", "timed_out": False, "duration_s": 0}
    if exe.lower().endswith((".cmd", ".bat")) and any(set(a) & BATCH_UNSAFE for a in argv[1:]):
        return {"status": "NOT RUN", "exit_code": None, "output": "blocked: an argument has characters that are unsafe for a .cmd/.bat launcher", "timed_out": False, "duration_s": 0}
    if cancel is not None and cancel.is_set():
        return {"status": "CANCELLED", "exit_code": None, "output": "stopped before it started", "timed_out": False, "duration_s": 0}
    started, timed_out, cancelled, orphans, leftovers = time.monotonic(), False, False, False, False
    try:
        proc = subprocess.Popen([exe, *argv[1:]], cwd=cwd, env=_env(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **proctree.popen_flags())
    except OSError as exc:
        return {"status": "NOT RUN", "exit_code": None, "output": f"could not start: {exc}", "timed_out": False, "duration_s": 0}
    guard = proctree.TreeGuard(proc)
    remove = cancel.on_cancel(guard.kill) if cancel is not None else (lambda: None)
    chunks, size = [], [0]

    def read_output():   # a thread, so a background process that keeps the pipe open can never block us after the command itself has ended
        for chunk in iter(lambda: proc.stdout.read(4096), b""):
            if size[0] < MAX_CAPTURE:
                chunks.append(chunk)
                size[0] += len(chunk)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        while True:
            try:
                proc.wait(timeout=0.25)
                break
            except subprocess.TimeoutExpired:
                cancelled = cancel is not None and cancel.is_set()
                timed_out = not cancelled and time.monotonic() - started > timeout
                if cancelled or timed_out:
                    guard.kill()
                    break
        reader.join(2.0)
        if reader.is_alive():   # the command is over but something it started still holds the pipe: that is a leftover, remove it
            leftovers = True
            guard.kill()
            reader.join(5.0)
            orphans = reader.is_alive()
        proc.wait(timeout=10)
    finally:
        remove()
        guard.close()
    cancelled = cancelled or (cancel is not None and cancel.is_set() and proc.returncode != 0)   # killed by Stop while we were waiting
    text = b"".join(chunks).decode("utf-8", "replace")
    if leftovers:
        text += "\n[note: a background process started by this command was still running and was stopped]"
    if orphans:
        text += "\n[WARNING: some child processes may still be running]"
    status = "CANCELLED" if cancelled else "PASSED" if proc.returncode == 0 and not timed_out else "FAILED"
    return {"status": status, "exit_code": proc.returncode, "timed_out": timed_out, "duration_s": round(time.monotonic() - started, 1),
            "output": clip_log(text, max_chars), **({"orphans_possible": True} if orphans else {})}
