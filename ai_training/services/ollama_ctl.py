"""Controls the local Ollama for a fair speed test: restart it (a clean GPU for each model) and check which models it can see.
Windows: ends Ollama and starts `ollama serve` again. Elsewhere, or if that fails, the caller falls back to unloading the model."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from typing import Callable

DEFAULT_URL = "http://localhost:11434"
DETACHED = 0x00000008 | 0x00000200 | 0x08000000   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW


def base_url() -> str:
    from core.models import AppSettings

    return str(AppSettings.get("ai_ollama_url", DEFAULT_URL, user=None) or DEFAULT_URL).strip().rstrip("/")


def normal(name: str) -> str:
    return name if ":" in name else name + ":latest"


def installed(url: str) -> set[str] | None:
    """Names of the models Ollama can see (None = Ollama does not answer)."""
    try:
        with urllib.request.urlopen(url + "/api/tags", timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return {normal(str(m.get("name") or m.get("model") or "")) for m in data.get("models", [])}


def wait_ready(url: str, seconds: int = 180) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if installed(url) is not None:
            return True
        time.sleep(2)
    return False


def restart(models_dir: str, url: str, log: Callable[[str], None]) -> bool:
    """True when Ollama was ended and is answering again. Ollama starts without its tray icon (open it from the Start menu if you want it)."""
    if os.name != "nt":
        return False
    try:
        for exe in ("ollama app.exe", "ollama.exe"):
            subprocess.run(["taskkill", "/F", "/T", "/IM", exe], capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
        time.sleep(5)
        env = dict(os.environ)
        if models_dir and not env.get("OLLAMA_MODELS"):
            env["OLLAMA_MODELS"] = models_dir
        subprocess.Popen(["ollama", "serve"], env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=DETACHED, close_fds=True)
    except (OSError, subprocess.SubprocessError) as exc:
        log(f"Could not restart Ollama: {type(exc).__name__}: {str(exc)[:120]}")
        return False
    return wait_ready(url)
