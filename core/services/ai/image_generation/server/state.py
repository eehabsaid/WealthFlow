"""Process bookkeeping for the managed image server: state file, cross-process lock, liveness, tree kill, server log.

Everything lives under <BASE_DIR>/runtime/image_server/ so every Django process (workers, reloader children, later restarts)
sees the same server and never starts a second one."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import time

from django.conf import settings

from .errors import ServerError

IS_WINDOWS = os.name == "nt"
LOG_MAX_BYTES = 2 * 1024 * 1024


def runtime_dir() -> str:
    path = os.path.join(settings.BASE_DIR, "runtime", "image_server")
    os.makedirs(path, exist_ok=True)
    return path


def _file(name: str) -> str:
    return os.path.join(runtime_dir(), name)


def log_path() -> str:
    return _file("server.log")


def read_state() -> dict | None:
    try:
        with open(_file("state.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) and isinstance(data.get("pid"), int) else None
    except (OSError, ValueError):
        return None


def write_state(state: dict) -> None:
    with open(_file("state.json"), "w", encoding="utf-8") as fh:
        json.dump(state, fh)


def clear_state() -> None:
    with contextlib.suppress(OSError):
        os.remove(_file("state.json"))


@contextlib.contextmanager
def file_lock(timeout: float):
    """Exclusive lock across processes, so two workers never start the server at the same time."""
    fh = open(_file("start.lock"), "a+b")
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                if IS_WINDOWS:
                    import msvcrt
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise ServerError("Another WealthFlow process is still starting the image server.") from None
                time.sleep(0.3)
        yield
    finally:
        try:
            if IS_WINDOWS:
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        fh.close()


def _open_process(pid: int):
    """Windows: a query-only handle to the process (None when it does not exist). Close it with kernel32.CloseHandle."""
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    return kernel32, (kernel32.OpenProcess(0x1000, False, pid) or None)   # PROCESS_QUERY_LIMITED_INFORMATION


def pid_alive(pid: int) -> bool:
    if IS_WINDOWS:
        import ctypes
        from ctypes import wintypes
        kernel32, handle = _open_process(pid)
        if not handle:
            return False
        code = wintypes.DWORD()
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259   # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:                                         # a finished child that was not reaped yet is not alive
        with open(f"/proc/{pid}/stat", encoding="utf-8") as fh:
            return fh.read().rsplit(")", 1)[1].split()[0] != "Z"
    except (OSError, IndexError):
        return True


def start_time(pid: int) -> float | None:
    """When the process started (seconds since epoch), or None if it cannot be read. Used so a recycled PID is never killed."""
    try:
        if IS_WINDOWS:
            import ctypes
            from ctypes import wintypes
            kernel32, handle = _open_process(pid)
            if not handle:
                return None
            created, a, b, c = (wintypes.FILETIME() for _ in range(4))
            kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
            ok = kernel32.GetProcessTimes(handle, *(ctypes.byref(x) for x in (created, a, b, c)))
            kernel32.CloseHandle(handle)
            return ((created.dwHighDateTime << 32 | created.dwLowDateTime) / 1e7 - 11644473600) if ok else None
        with open(f"/proc/{pid}/stat", encoding="utf-8") as fh:
            ticks = int(fh.read().rsplit(")", 1)[1].split()[19])
        with open("/proc/stat", encoding="utf-8") as fh:
            boot = next(int(line.split()[1]) for line in fh if line.startswith("btime"))
        return boot + ticks / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, StopIteration, IndexError, AttributeError):
        return None


def is_same_process(state: dict) -> bool:
    """The recorded server is still the very process we started (alive AND the same start time)."""
    pid, recorded = state.get("pid"), state.get("start_time")
    if not isinstance(pid, int) or not pid_alive(pid):
        return False
    now = start_time(pid)
    return recorded is not None and now is not None and abs(now - float(recorded)) < 3


def kill_tree(pid: int, force: bool) -> None:
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/PID", str(pid), "/T"] + (["/F"] if force else []), capture_output=True, check=False,
                       creationflags=0x08000000)
        return
    import signal
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(os.getpgid(pid), signal.SIGKILL if force else signal.SIGTERM)


def log_tail(lines: int = 12, limit: int = 700) -> str:
    try:
        with open(log_path(), "rb") as fh:
            fh.seek(max(0, os.path.getsize(log_path()) - 8192))
            text = fh.read().decode("utf-8", "replace")
    except OSError:
        return ""
    return " | ".join(line.strip() for line in text.splitlines()[-lines:] if line.strip())[-limit:]
