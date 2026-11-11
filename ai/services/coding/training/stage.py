"""Point 10: a coding-only fine-tune of the ORIGINAL base model, kept apart from the business training (own run folder and own model name).
It reuses the proven machinery of ai_training (WSL trainer, GGUF export, Ollama registration) and only supplies the coding examples.
It never switches the model in Settings."""

from __future__ import annotations

import json
import os
from typing import Callable

from ai.services.coding.training import settings


def train_config(cfg_settings: dict | None = None, cfg_path: str | None = None):
    """`cfg_path`, when given, loads a complete, standalone TrainConfig file (same shape as ai/training/profiles/recovery.json) with no
    overrides - used by the ledger-based coding_agent model, which needs its own original/best/new model names and its own adapter to
    continue from, not just a different suffix. Otherwise `cfg_settings` (default: the coding-dataset settings, coding_agent/training.json)
    overrides just model_suffix/min_traces on top of the default ai/training/config.json, as before."""
    from ai.training.services import config

    if cfg_path:
        return config.load(path=cfg_path)
    s = cfg_settings if cfg_settings is not None else settings()
    # original_model/best_model/new_model default to "" here even though the shared base config.json (ai/training/config.json) sets them for
    # the UNRELATED business-agent2 training: without this, this stage would silently inherit that other family's model names.
    return config.load(model_suffix=s["model_suffix"], min_traces=s["min_examples"],
                        original_model=s.get("original_model", ""), best_model=s.get("best_model", ""), new_model=s.get("new_model", ""))


def names(current_model: str, cfg) -> tuple[str, str]:
    """(original model, new model): new = cfg.new_model if the config set one, else original + the suffix; original = cfg.original_model if
    set, else current_model with any trained suffix stripped. The explicit-override path lets a profile (like the ledger-based coding_agent
    model) register under a name of its own choosing while still branching from, and registering beside, whichever model it continues from."""
    from ai.training.services import ollama_stage

    original = ollama_stage.base_name(current_model, cfg)
    return original, (cfg.new_model or ollama_stage.new_name(original, cfg.model_suffix))


def count_lines(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())
    except OSError:
        return 0


def run(train_file: str, current_model: str, *, dry_run: bool = False, fresh: bool = False, log: Callable[[str], None] = print,
        cfg_settings: dict | None = None, cfg_path: str | None = None, example_label: str = "verified coding examples",
        too_few_hint: str = "This repo's history gives too few verified changes to teach a model. Keep adding small, tested commits and run the dataset stage again.") -> dict:
    from ai.training.services import ollama_stage, preflight, train_stage, wsl
    from ai.training.services.config import REPO_ROOT

    cfg, count = train_config(cfg_settings, cfg_path), count_lines(train_file)
    original, new_model = names(current_model, cfg)
    Check = preflight.Check
    checks = [Check(example_label, count >= cfg.min_traces, f"{count} (need {cfg.min_traces})", too_few_hint)]
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
        if wsl.stream(cfg, f"tr -d '\\r' < {repo}/ai/training/trainer/setup_env.sh | bash", log) != 0:
            return {"status": "setup_failed", "model": ""}
        cmd = f"cd {repo} && $HOME/ai_training_venv/bin/python -m ai.training.trainer.train --config {wsl.quote(wsl.to_wsl_path(config_path))}"
        log(f"Training on {count} verified coding examples ...")
        if wsl.stream(cfg, cmd, log) != 0:
            return {"status": "training_failed", "model": ""}
    exported = train_stage.finished_export(cfg)
    if not (exported["gguf"] and exported["mmproj"] and exported["vision_assets"]):
        return {"status": "incomplete_export", "model": ""}
    ok = ollama_stage.register(original, exported["gguf_files"] or [exported["gguf"]], exported["mmproj"], new_model, run_dir, log)
    return {"status": "trained" if ok else "register_failed", "model": new_model if ok else ""}
