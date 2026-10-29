"""Checks before the long training run. Each failed check says in plain words what to do. Nothing here changes anything."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
from dataclasses import dataclass

from . import wsl

APT_LINE = "wsl sudo apt install -y build-essential cmake curl git libcurl4-openssl-dev"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""


def _free_gb(path: str) -> float:
    probe = os.path.abspath(path)
    while probe and not os.path.exists(probe) and os.path.dirname(probe) != probe:
        probe = os.path.dirname(probe)
    return shutil.disk_usage(probe).free / 1024 ** 3


def _ollama_has(model: str) -> bool:
    try:
        return subprocess.run(["ollama", "show", model], capture_output=True, timeout=60, stdin=subprocess.DEVNULL).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def base_checks(cfg, traces: int, ollama_model: str) -> list[Check]:
    shards = glob.glob(os.path.join(cfg.base_model_dir, "*.safetensors"))
    free = _free_gb(cfg.work_dir)
    return [
        Check("proven traces", traces >= cfg.min_traces, f"{traces} (need {cfg.min_traces})",
              "Run `python manage.py ai_training` without --limit so more questions are asked."),
        Check("base model files", bool(shards) and os.path.exists(os.path.join(cfg.base_model_dir, "config.json")),
              f"{len(shards)} weight files in {cfg.base_model_dir}", "Download Qwen/Qwen3.8-27B into that folder, or fix base_model_dir in ai_training/config.json."),
        Check("free disk", free >= cfg.min_free_gb, f"{free:.0f} GB free where {cfg.work_dir} is (need {cfg.min_free_gb})",
              "Free disk space, or point work_dir in ai_training/config.json to a bigger drive."),
        Check("Ollama model", _ollama_has(ollama_model), ollama_model, "Start Ollama and set the model name in Settings > AI Advisor."),
    ]


def wsl_checks(cfg) -> list[Check]:
    if not wsl.available():
        return [Check("WSL2", False, "wsl.exe not found", "Open PowerShell as administrator, run `wsl --install -d Ubuntu`, restart the PC, run this command again.")]
    if not wsl.distros():
        return [Check("WSL2 Ubuntu", False, "no Linux system found, or WSL did not answer in 20 seconds (WSL is probably not installed)",
                      "Open PowerShell as administrator, run `wsl --install -d Ubuntu`, restart the PC, open Ubuntu once to finish its setup, run this command again.")]
    code, out = wsl.capture(cfg, "nvidia-smi -L")
    gpu = Check("GPU inside WSL", code == 0 and "GPU" in out, out.splitlines()[0] if out else "no answer",
                "Update the NVIDIA driver on Windows (it also serves WSL), then run `wsl --shutdown` and try again.")
    code, out = wsl.capture(cfg, "for t in gcc cmake make curl git; do command -v $t >/dev/null || echo $t; done")
    tools = Check("Linux build tools", code == 0 and not out, f"missing: {out}" if out else "all present", f"Run once: {APT_LINE}")
    code, out = wsl.capture(cfg, "awk '/MemTotal/ {print int($2/1048576)}' /proc/meminfo")
    have = int(out) if out.isdigit() else 0
    memory = Check("WSL memory", have >= cfg.wsl_memory_gb - 4, f"{have} GB for WSL (want about {cfg.wsl_memory_gb})",
                   f"Create {os.path.expanduser('~/.wslconfig')} with:  [wsl2]  memory={cfg.wsl_memory_gb}GB  then run `wsl --shutdown`.")
    return [gpu, tools, memory]


def failed(checks: list[Check]) -> list[Check]:
    return [c for c in checks if not c.ok]


def describe(checks: list[Check]) -> list[str]:
    return [f"[{'OK' if c.ok else 'FIX'}] {c.name}: {c.detail}" + (f"\n      -> {c.fix}" if not c.ok and c.fix else "") for c in checks]
