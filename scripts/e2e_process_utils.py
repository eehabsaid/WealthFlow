"""
Small generic process/logging/file-diff helpers for run_full_e2e.py.

Split out of the former monolithic scripts/run_full_e2e.py (200-line
rule). Kept as a flat sibling file — scripts/ has no existing
subfolder-per-script convention for standalone CLI entry points (unlike
tests/modules/, which does use subfolders), and run_full_e2e.py must
remain directly invocable as `python scripts/run_full_e2e.py`.
"""

from __future__ import annotations

import os
import signal
import sys
import time
import urllib.request
import urllib.error


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


def install_signal_handlers() -> None:
    def _handle(signum, frame):
        raise KeyboardInterrupt(f"received signal {signum}")

    signal.signal(signal.SIGTERM, _handle)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _handle)
