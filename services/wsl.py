"""Talking to WSL2 (Linux inside Windows) from the Windows side. Every call goes through `wsl.exe`."""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
from typing import Callable


def to_wsl_path(path: str) -> str:
    """D:\\AI\\x -> /mnt/d/AI/x (a path that is already Linux style is returned unchanged)."""
    match = re.match(r"^([A-Za-z]):[\\/]*(.*)$", path)
    if not match:
        return path
    return f"/mnt/{match.group(1).lower()}/" + match.group(2).replace("\\", "/")


def from_wsl_path(path: str) -> str:
    match = re.match(r"^/mnt/([a-z])/(.*)$", path)
    return f"{match.group(1).upper()}:\\" + match.group(2).replace("/", "\\") if match else path


def decode(raw: bytes) -> str:
    """wsl.exe prints some answers in UTF-16."""
    return (raw.decode("utf-16-le", errors="replace") if b"\x00" in raw else raw.decode("utf-8", errors="replace")).replace("\x00", "")


def available() -> bool:
    return bool(shutil.which("wsl.exe") or shutil.which("wsl"))


def _run(cmd: list[str], timeout: int):
    """subprocess.run that never waits for keyboard input and never raises: None = no answer in time / cannot start."""
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except (subprocess.TimeoutExpired, OSError):
        return None


def distros() -> list[str]:
    """Installed Linux systems; [] when there is none or WSL does not answer (it is then not installed or not working)."""
    done = _run(["wsl.exe", "-l", "-q"], 20)
    if done is None or done.returncode != 0:
        return []
    return [line.strip() for line in decode(done.stdout).splitlines() if line.strip()]


def _command(cfg, script: str) -> list[str]:
    return ["wsl.exe"] + (["-d", cfg.wsl_distro] if cfg.wsl_distro else []) + ["--", "bash", "-lc", script]


def capture(cfg, script: str, timeout: int = 60) -> tuple[int, str]:
    done = _run(_command(cfg, script), timeout)
    if done is None:
        return 124, f"WSL gave no answer within {timeout} seconds"
    return done.returncode, decode(done.stdout + done.stderr).strip()


def stream(cfg, script: str, log: Callable[[str], None]) -> int:
    """Runs a long command and passes every output line to `log` as it appears."""
    proc = subprocess.Popen(_command(cfg, script), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    for raw in proc.stdout:
        text = decode(raw).rstrip()
        if text:
            log(text)
    return proc.wait()


def shutdown() -> None:
    _run(["wsl.exe", "--shutdown"], 60)


def quote(value: str) -> str:
    return shlex.quote(value)
