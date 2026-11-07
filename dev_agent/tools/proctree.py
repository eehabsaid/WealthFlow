"""Kill a command AND everything it started, so Stop never leaves orphans.
Windows: every command runs inside a Job Object with KILL_ON_JOB_CLOSE (all descendants die with the job, even if this server is killed),
with `taskkill /T /F` as a second line. POSIX: the command is a session leader and its whole process group is killed (SIGTERM, then SIGKILL)."""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time

NT = os.name == "nt"
CREATE_NO_WINDOW = 0x08000000
_active: set = set()
_lock = threading.Lock()


def popen_flags() -> dict:
    if NT:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW}
    return {"start_new_session": True}


def pid_alive(pid: int) -> bool:
    """True if a process with this id is running. (os.kill(pid, 0) would TERMINATE the process on Windows, so it is never used there.)"""
    if NT:
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x1000, False, int(pid))   # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.get_last_error() == 5                # access denied: it exists
        code = ctypes.c_ulong()
        ok = kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))
        kernel.CloseHandle(ctypes.c_void_p(handle))
        return bool(ok) and code.value == 259                  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:   # Linux: a finished process that nobody has collected yet (zombie) still answers kill(pid, 0), but it is not running
        with open(f"/proc/{int(pid)}/stat", "rb") as handle:
            return handle.read().rsplit(b")", 1)[1].split()[0] not in (b"Z", b"X")
    except (OSError, IndexError):
        return True


def _make_job(proc):
    """A Job Object holding `proc`, or None (then taskkill /T is the only mechanism)."""
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class IoCounters(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint64) for n in ("ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")]

    class Extended(ctypes.Structure):
        _fields_ = [("Basic", Basic), ("Io", IoCounters), ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateJobObjectW.restype = wintypes.HANDLE
    k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    job = k.CreateJobObjectW(None, None)
    if not job:
        return None
    info = Extended()
    info.Basic.LimitFlags = 0x2000   # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not k.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)) or not k.AssignProcessToJobObject(job, int(proc._handle)):
        k.CloseHandle(job)
        return None
    return job


class TreeGuard:
    """Owns one running command's process tree. kill() ends it and every descendant; close() (always called) also removes leftovers."""

    def __init__(self, proc: subprocess.Popen):
        self.proc, self._job, self._closed = proc, _make_job(proc) if NT else None, False
        with _lock:
            _active.add(self)

    def kill(self) -> None:
        if NT:
            if self._job:
                import ctypes
                ctypes.WinDLL("kernel32").TerminateJobObject(ctypes.c_void_p(self._job), 1)
            subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], capture_output=True, timeout=30, creationflags=CREATE_NO_WINDOW)
            return
        for sig, grace in ((signal.SIGTERM, 1.0), (signal.SIGKILL, 0)):
            try:
                os.killpg(self.proc.pid, sig)
            except (ProcessLookupError, PermissionError):
                return
            deadline = time.monotonic() + grace
            while grace and time.monotonic() < deadline:
                try:
                    os.killpg(self.proc.pid, 0)
                except ProcessLookupError:
                    return
                time.sleep(0.05)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        with _lock:
            _active.discard(self)
        if NT:
            if self._job:
                import ctypes
                ctypes.WinDLL("kernel32").CloseHandle(ctypes.c_void_p(self._job))   # KILL_ON_JOB_CLOSE removes anything still running
        else:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)                              # background leftovers of a finished command
            except (ProcessLookupError, PermissionError):
                pass


def kill_all() -> int:
    """Kill every command still running (server shutdown, Ctrl-C, interpreter exit)."""
    with _lock:
        guards = list(_active)
    for guard in guards:
        try:
            guard.kill()
        except Exception:
            pass
    return len(guards)
