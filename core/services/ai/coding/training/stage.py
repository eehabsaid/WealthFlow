"""Point 10: a coding-only fine-tune of the ORIGINAL base model, kept apart from the business training (own run folder and own model name).
It reuses the proven machinery of ai_training (WSL trainer, GGUF export, Ollama registration) and only supplies the coding examples.
It never switches the model in Settings."""

from __future__ import annotations

import json
import os
from typing import Callable

from . import settings


def train_config():
    from ai_training.services import config

    return config.load(model_suffix=settings()["model_suffix"], min_traces=settings()["min_examples"])


def names(current_model: str, cfg) -> tuple[str, str]:
    """(original model, new coding model): the new name = the original + the coding suffix, so no earlier model is ever overwritten."""
    from ai_training.services import ollama_stage

    original = ollama_stage.base_name(current_model, cfg)
    return original, ollama_stage.new_name(original, cfg.model_suffix)


def count_lines(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())
    except OSError:
        return 0


def run(train_file: str, current_model: str, *, dry_run: bool = False, fresh: bool = False, log: Callable[[str], None] = print) -> dict:
    from ai_training.services import ollama_stage, preflight, train_stage, wsl
    from ai_training.services.config import REPO_ROOT

    cfg, count = train_config(), count_lines(train_file)
    original, new_model = names(current_model, cfg)
    Check = preflight.Check
    checks = [Check("verified coding examples", count >= cfg.min_traces, f"{count} (need {cfg.min_traces})",
                    "This repo's history gives too few verified changes to teach a model. Keep adding small, tested commits and run the dataset stage again.")]
    checks += preflight.base_checks(cfg, count, original)[1:] + preflight.wsl_checks(cfg)
    for line in preflight.describe(checks):
        log(line)
    if preflight.failed(checks):
        return {"status": "blocked", "model": ""}
    run_dir = train_stage.run_dir(cfg)
    os.makedirs(run_dir, exist_ok=True)
    wsl_cfg = {**cfg.as_dict(), "base_model_dir": wsl.to_wsl_path(cfg.base_model_dir), "train_file": wsl.to_wsl_path(train_file),
               "out_dir": wsl.to_wsl_path(os.path.join(run_dir, "out"))}
    config_path = os.path.join(run_dir, "run_config.json")
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(wsl_cfg, fh, indent=4)
    if dry_run:
        train_stage.dry_stats(cfg, train_file, log)
        log("Dry run: everything above is ready. " + train_stage.ESTIMATE)
        return {"status": "dry_run", "model": new_model}
    if not fresh and train_stage.finished_model(cfg):
        log("An earlier coding training run is finished: reusing it (use --fresh to train again).")
    else:
        train_stage.free_gpu(original, log)
        repo = wsl.quote(wsl.to_wsl_path(REPO_ROOT))
        log(f"Preparing the training tools inside WSL (first time only) ... {train_stage.ESTIMATE}")
        if wsl.stream(cfg, f"tr -d '\\r' < {repo}/ai_training/trainer/setup_env.sh | bash", log) != 0:
            return {"status": "setup_failed", "model": ""}
        cmd = f"cd {repo} && $HOME/ai_training_venv/bin/python -m ai_training.trainer.train --config {wsl.quote(wsl.to_wsl_path(config_path))}"
        log(f"Training on {count} verified coding examples ...")
        if wsl.stream(cfg, cmd, log) != 0:
            return {"status": "training_failed", "model": ""}
    exported = train_stage.finished_export(cfg)
    if not (exported["gguf"] and exported["mmproj"] and exported["vision_assets"]):
        return {"status": "incomplete_export", "model": ""}
    ok = ollama_stage.register(original, exported["gguf_files"] or [exported["gguf"]], exported["mmproj"], new_model, run_dir, log)
    return {"status": "trained" if ok else "register_failed", "model": new_model if ok else ""}
