"""Best-effort local hardware detection (CPU, RAM, GPU) — stdlib only, no
new dependency (psutil is NOT in requirements.txt, so it must not be relied
on: it happens to be present in this sandbox but may not be on Ehab's actual
deploy target). Every field degrades to None on any platform/permission
failure rather than raising — this feeds a *recommendation*, never a
required value, so a partial/unknown read must never break settings.
"""

from __future__ import annotations

import ctypes
import os
import platform
import subprocess


def _total_ram_gb() -> float | None:
    system = platform.system()
    try:
        if system == "Windows":
            # No stdlib RAM query on Windows — GlobalMemoryStatusEx via ctypes
            # avoids needing psutil or any third-party package.
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
                return round(stat.ullTotalPhys / (1024 ** 3), 1)
            return None
        if system == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return round(kb / (1024 ** 2), 1)
            return None
        if system == "Darwin":
            out = subprocess.run(
                ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=3
            )
            if out.returncode == 0 and out.stdout.strip():
                return round(int(out.stdout.strip()) / (1024 ** 3), 1)
            return None
    except Exception:
        return None
    return None


def _gpu_vram_gb() -> float | None:
    """nvidia-smi only — a shared/integrated GPU (Ehab's actual dev machine)
    has no discrete VRAM to query this way and correctly reports None; the
    caller treats None as "assume no dedicated GPU headroom", not an error."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
        )
        if out.returncode == 0 and out.stdout.strip():
            first_line = out.stdout.strip().splitlines()[0]
            return round(int(first_line.strip()) / 1024, 1)
    except (FileNotFoundError, subprocess.SubprocessError, ValueError, OSError):
        pass
    return None


def detect_hardware() -> dict:
    """Never raises. Any field may be None if it couldn't be determined."""
    return {
        "cpu_count": os.cpu_count(),
        "total_ram_gb": _total_ram_gb(),
        "gpu_vram_gb": _gpu_vram_gb(),
        "platform": platform.system() or None,
    }
