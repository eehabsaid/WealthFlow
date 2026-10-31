"""Registers the trained model file in Ollama under a NEW name. The chat template and every setting (including your 150k context) are
copied from the model you run today, so the new model behaves like it; only the weights differ. Nothing is switched automatically."""

from __future__ import annotations

import os
import subprocess
from typing import Callable


def base_name(current: str, cfg) -> str:
    """The model without any trained suffix ("m-agent2" / "m-agent" -> "m"): the ORIGINAL model new training starts from and registers beside."""
    if cfg.original_model:
        return cfg.original_model
    for suffix in sorted((cfg.model_suffix, *cfg.previous_suffixes), key=len, reverse=True):
        if suffix and current.endswith(suffix):
            return current[: -len(suffix)]
    return current


def new_name(current: str, suffix: str) -> str:
    return current if current.endswith(suffix) else current + suffix


def rewrite_modelfile(text: str, gguf_path: str) -> str:
    """The current model's Modelfile with ONE `FROM <gguf>`; extra FROM lines (e.g. a vision part) are dropped, TEMPLATE blocks kept."""
    out, in_block, wrote = [], False, False
    for line in text.splitlines():
        if not in_block and line.startswith("FROM "):
            if not wrote:
                out.append(f"FROM {gguf_path}")
                wrote = True
            continue
        if line.count('"""') % 2 == 1:
            in_block = not in_block
        out.append(line)
    if not wrote:
        out.insert(0, f"FROM {gguf_path}")
    return "\n".join(out) + "\n"


def register(current_model: str, gguf_path: str, name: str, work_dir: str, log: Callable[[str], None]) -> bool:
    shown = subprocess.run(["ollama", "show", current_model, "--modelfile"], capture_output=True, timeout=120)
    if shown.returncode != 0:
        log(f"Cannot read the Modelfile of {current_model}: {shown.stderr.decode('utf-8', 'replace')[:200]}")
        return False
    path = os.path.join(work_dir, "Modelfile.new")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(rewrite_modelfile(shown.stdout.decode("utf-8", "replace"), gguf_path))
    made = subprocess.run(["ollama", "create", name, "-f", path], capture_output=True, timeout=7200)
    log((made.stdout + made.stderr).decode("utf-8", "replace").strip()[-300:])
    return made.returncode == 0
