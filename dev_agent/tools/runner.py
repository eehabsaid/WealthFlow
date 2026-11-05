"""Run one command as an argv list (never through a shell), with a timeout, a clean environment and the whole process tree killed on timeout.
Works on Windows 11 (.cmd/.bat shims such as npx and eslint are resolved with PATHEXT and their arguments checked) and POSIX."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time

from ..engine.budget import clip_log

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


def _kill_tree(proc: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=30)
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        proc.kill()


def run(argv: list[str], cwd, timeout: int, max_chars: int = 6000) -> dict:
    exe = resolve_exe(argv[0])
    if not exe:
        return {"status": "NOT RUN", "exit_code": None, "output": f"executable not found: {argv[0]}", "timed_out": False, "duration_s": 0}
    if exe.lower().endswith((".cmd", ".bat")) and any(set(a) & BATCH_UNSAFE for a in argv[1:]):
        return {"status": "NOT RUN", "exit_code": None, "output": "blocked: an argument has characters that are unsafe for a .cmd/.bat launcher", "timed_out": False, "duration_s": 0}
    flags = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    started, timed_out = time.monotonic(), False
    try:
        proc = subprocess.Popen([exe, *argv[1:]], cwd=cwd, env=_env(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **flags)
    except OSError as exc:
        return {"status": "NOT RUN", "exit_code": None, "output": f"could not start: {exc}", "timed_out": False, "duration_s": 0}
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(proc)
        out, _ = proc.communicate()
    text = out.decode("utf-8", "replace")
    return {"status": "PASSED" if proc.returncode == 0 and not timed_out else "FAILED", "exit_code": proc.returncode, "timed_out": timed_out,
            "duration_s": round(time.monotonic() - started, 1), "output": clip_log(text, max_chars)}
