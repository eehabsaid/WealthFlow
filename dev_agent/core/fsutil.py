"""File helpers that behave the same on Windows 11 and POSIX: atomic writes, retrying replace, portable lock files, newline-preserving text."""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import tempfile
import time
from pathlib import Path


class LockTimeout(RuntimeError):
    pass


def _current_umask() -> int:
    mask = os.umask(0)   # read once at import (nothing else is running yet); toggling it later would briefly change the mask of other threads
    os.umask(mask)
    return mask


UMASK = _current_umask()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bytes(path) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


def decode(data: bytes) -> tuple[str, bool]:
    """(text with \\n newlines, file used CRLF). UnicodeDecodeError for binary files."""
    text = data.decode("utf-8")
    crlf = b"\r\n" in data and data.count(b"\r\n") * 2 > data.count(b"\n")
    return text.replace("\r\n", "\n"), crlf


def encode(text: str, crlf: bool) -> bytes:
    return (text.replace("\n", "\r\n") if crlf else text).encode("utf-8")


def replace_retry(src, dst, tries: int = 8) -> None:
    """os.replace that waits out the short PermissionErrors Windows raises while an editor, indexer or antivirus holds the file."""
    for attempt in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == tries - 1:
                raise
            time.sleep(0.05 * 2 ** attempt)


def atomic_write(path, data: bytes) -> None:
    """Write to a temp file in the same folder, flush to disk, then replace; the target is never left half-written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".devagent-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if existed:
            shutil.copymode(path, tmp)
        else:
            os.chmod(tmp, 0o666 & ~UMASK)
        replace_retry(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _owner_is_gone(name: Path) -> bool:
    """True when the lock file names a process id that is not running. An unreadable or half-written file is left to the age rule."""
    from ..tools.proctree import pid_alive   # imported here: the tools package imports this module
    try:
        pid = int(name.read_text(encoding="ascii").split()[0])
    except (OSError, ValueError, IndexError):
        return False
    return pid > 0 and not pid_alive(pid)


@contextlib.contextmanager
def file_lock(lock_dir, key: str, timeout: float = 30.0, stale: float = 600.0):
    """Cross-platform advisory lock: an exclusively created lock file named after `key`. A lock whose process no longer exists (it crashed while
    holding it) is broken at once; any lock older than `stale` seconds is broken too."""
    lock_dir = Path(lock_dir)
    lock_dir.mkdir(parents=True, exist_ok=True)
    name = lock_dir / (hashlib.sha1(key.lower().encode("utf-8")).hexdigest()[:24] + ".lock")
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(name, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {time.time()}".encode())
            os.close(fd)
            break
        except FileExistsError:
            with contextlib.suppress(OSError):
                if time.time() - name.stat().st_mtime > stale or _owner_is_gone(name):
                    name.unlink()
                    continue
            if time.monotonic() > deadline:
                raise LockTimeout(f"could not lock {key} within {timeout:.0f}s") from None
            time.sleep(0.05)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            name.unlink()


@contextlib.contextmanager
def lock_many(lock_dir, keys, timeout: float = 30.0):
    """Lock several keys in sorted order (no deadlock between two writers)."""
    with contextlib.ExitStack() as stack:
        for key in sorted(set(keys)):
            stack.enter_context(file_lock(lock_dir, key, timeout))
        yield
