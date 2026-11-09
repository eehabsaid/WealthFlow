"""Registers the trained GGUF and vision projector under a NEW Ollama name.

The chat template and every setting (including the 150k context) come from the original model. Nothing is switched automatically.
"""

from __future__ import annotations

import os
import subprocess
from typing import Callable, Sequence


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


def rewrite_modelfile(text: str, gguf_paths: Sequence[str] | str, mmproj_path: str) -> str:
    """Replace inherited model layers with the exported GGUF shards and vision projector."""
    if isinstance(gguf_paths, str):
        gguf_paths = [gguf_paths]
    if not gguf_paths:
        raise ValueError("at least one model GGUF is required")
    if not mmproj_path:
        raise ValueError("a vision projector GGUF is required")
    layers = [f"FROM {path}" for path in (*gguf_paths, mmproj_path)]
    out, in_block, wrote = [], False, False
    for line in text.splitlines():
        if not in_block and line.startswith("FROM "):
            if not wrote:
                out.extend(layers)
                wrote = True
            continue
        if line.count('"""') % 2 == 1:
            in_block = not in_block
        out.append(line)
    if not wrote:
        out[0:0] = layers
    return "\n".join(out) + "\n"


def register(
    current_model: str,
    gguf_paths: Sequence[str] | str,
    mmproj_path: str,
    name: str,
    work_dir: str,
    log: Callable[[str], None],
) -> bool:
    if isinstance(gguf_paths, str):
        gguf_paths = [gguf_paths]
    missing = [path for path in (*gguf_paths, mmproj_path) if not os.path.isfile(path)]
    if not gguf_paths:
        missing.append("model GGUF")
    if not mmproj_path:
        missing.append("vision projector GGUF")
    if missing:
        log(f"Cannot register {name}: exported model/projector files are missing: {', '.join(missing)}")
        return False

    listed = subprocess.run(["ollama", "list"], capture_output=True, timeout=120)
    if listed.returncode != 0:
        log(f"Cannot verify that {name} is new: {listed.stderr.decode('utf-8', 'replace')[:200]}")
        return False
    list_lines = [line.split() for line in listed.stdout.decode("utf-8", "replace").splitlines() if line.split()]
    if not list_lines or list_lines[0][0].upper() != "NAME":
        log(f"Cannot verify that {name} is new: Ollama returned an unexpected model list.")
        return False
    existing_names = {line[0] for line in list_lines[1:]}
    if name in existing_names:
        log(f"Cannot register {name}: that Ollama model already exists, so it was left unchanged.")
        return False

    shown = subprocess.run(["ollama", "show", current_model, "--modelfile"], capture_output=True, timeout=120)
    if shown.returncode != 0:
        log(f"Cannot read the Modelfile of {current_model}: {shown.stderr.decode('utf-8', 'replace')[:200]}")
        return False
    path = os.path.join(work_dir, "Modelfile.new")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(rewrite_modelfile(shown.stdout.decode("utf-8", "replace"), gguf_paths, mmproj_path))
    made = subprocess.run(["ollama", "create", name, "-f", path], capture_output=True, timeout=7200)
    log((made.stdout + made.stderr).decode("utf-8", "replace").strip()[-300:])
    return made.returncode == 0
