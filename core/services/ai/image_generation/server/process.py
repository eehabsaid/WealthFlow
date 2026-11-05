"""Turn the saved start command into a running, detached, windowless process whose output goes to the server log."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess

from . import state
from .errors import ServerError

CREATE_NO_WINDOW, CREATE_NEW_PROCESS_GROUP, DETACHED_PROCESS = 0x08000000, 0x00000200, 0x00000008


def _split_windows(text: str) -> list[str]:
    """Windows command line: split on spaces outside double quotes, drop the quotes, keep backslashes (paths such as
    --extra-model-paths-config="D:\\AI Models\\x.yaml" stay one argument)."""
    args, current, quoted, started = [], [], False, False
    for ch in text:
        if ch == '"':
            quoted, started = not quoted, True
        elif ch.isspace() and not quoted:
            if started:
                args.append("".join(current))
                current, started = [], False
        else:
            current.append(ch)
            started = True
    if quoted:
        raise ValueError("unbalanced quotes")
    if started:
        args.append("".join(current))
    return args


def build_args(template: str, endpoint: str) -> list[str]:
    """Argument list for the command. {host} and {port} are filled from the saved API URL (so they are written only once)."""
    host, port = state.host_port(endpoint)
    text = str(template or "").replace("{host}", host).replace("{port}", port).strip()
    try:
        args = _split_windows(text) if state.IS_WINDOWS else shlex.split(text)
    except ValueError:
        raise ServerError("The server start command has unbalanced quotes.") from None
    if not args:
        raise ServerError("The server start command is empty.")
    return args


def check_executable(args: list[str]) -> None:
    if not (os.path.isfile(args[0]) or shutil.which(args[0])):
        raise ServerError(f"The server start command's program was not found: {args[0]}")


def working_dir(args: list[str]) -> str | None:
    script = next((a for a in args[1:] if a.lower().endswith(".py") and os.path.isfile(a)), None)
    path = os.path.dirname(os.path.abspath(script or args[0]))
    return path if os.path.isdir(path) else None


def spawn(args: list[str], key: str) -> subprocess.Popen:
    """Detached and windowless: no console window, nothing the user has to keep open; stdout/stderr go to the server log."""
    path = state.log_path(key)
    if os.path.exists(path) and os.path.getsize(path) > state.LOG_MAX_BYTES:
        os.replace(path, path + ".old")
    log = open(path, "ab")
    log.write(f"\n=== starting: {' '.join(args)[:400]}\n".encode("utf-8", "replace"))
    log.flush()
    kwargs = {"creationflags": CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP} if state.IS_WINDOWS else {"start_new_session": True}
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    try:
        return subprocess.Popen(args, cwd=working_dir(args), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env, **kwargs)
    except OSError as exc:
        raise ServerError(f"The image server could not be started: {exc.strerror or exc}") from None
    finally:
        log.close()
