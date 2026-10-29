"""The training stage: checks -> data file -> (WSL) environment -> QLoRA training + export -> result. Resumes: a finished run is reused."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Callable

from . import export, preflight, wsl
from .config import REPO_ROOT, TrainConfig

ESTIMATE = "Unmeasured estimate: several hours for a few hundred examples; the merge/export at the end needs lots of disk and memory."


def run_dir(cfg: TrainConfig) -> str:
    return os.path.join(cfg.work_dir, "current")


def write_inputs(cfg: TrainConfig, user) -> tuple[str, int]:
    os.makedirs(run_dir(cfg), exist_ok=True)
    train_file = os.path.join(run_dir(cfg), "train.jsonl")
    count = export.export_jsonl(train_file, user)
    wsl_cfg = {**cfg.as_dict(), "base_model_dir": wsl.to_wsl_path(cfg.base_model_dir), "train_file": wsl.to_wsl_path(train_file),
               "out_dir": wsl.to_wsl_path(os.path.join(run_dir(cfg), "out"))}
    path = os.path.join(run_dir(cfg), "run_config.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(wsl_cfg, fh, indent=4)
    return path, count


def finished_model(cfg: TrainConfig) -> str:
    """Windows path of the model file of an earlier finished run ("" if none)."""
    path = os.path.join(run_dir(cfg), "out", "result.json")
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        gguf = wsl.from_wsl_path(json.load(fh).get("gguf", ""))
    return gguf if gguf and os.path.exists(gguf) else ""


def free_gpu(ollama_model: str, log: Callable[[str], None]) -> None:
    """Training needs the whole GPU: unload the model Ollama keeps in memory after the last question (it stays up to 30 minutes)."""
    try:
        done = subprocess.run(["ollama", "stop", ollama_model], capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
        log(f"Unloaded {ollama_model} from the GPU." if done.returncode == 0 else f"Could not unload {ollama_model} (maybe not loaded): continuing.")
    except (OSError, subprocess.SubprocessError):
        log("Could not ask Ollama to unload the model: continuing.")


def dry_stats(cfg: TrainConfig, train_file: str, log: Callable[[str], None]) -> None:
    """How many examples fit the length limit, counted with the real tokenizer (no GPU needed). Skipped if `transformers` is missing here."""
    try:
        from transformers import AutoTokenizer

        from ai_training.trainer import render

        tok = AutoTokenizer.from_pretrained(cfg.base_model_dir)
        tok = getattr(tok, "tokenizer", tok)
        render.find_markers(tok, cfg.enable_thinking)
        _, stats = render.render_file(train_file, tok, cfg.max_seq_length, cfg.enable_thinking)
        log(f"Length check: {stats['kept']} of {stats['lines']} examples fit {cfg.max_seq_length} tokens (too long: {stats['too_long']}, longest {stats['max_tokens']}).")
    except Exception as exc:   # transformers missing, tokenizer not loadable, template surprise: say it, do not stop
        log(f"Length check skipped: {type(exc).__name__}: {str(exc)[:160]}")


def run(cfg: TrainConfig, user, ollama_model: str, *, dry_run: bool = False, fresh: bool = False, log: Callable[[str], None] = print) -> dict:
    traces = len(export.kept_traces(user))
    checks = preflight.base_checks(cfg, traces, ollama_model) + preflight.wsl_checks(cfg)
    if not dry_run and any(c.name == "WSL memory" and not c.ok for c in checks) and preflight.set_wsl_memory(cfg):
        log(f"Giving WSL {cfg.wsl_memory_gb} GB of memory in {preflight.wslconfig_path()} and restarting WSL ...")
        wsl.shutdown()
        checks = preflight.base_checks(cfg, traces, ollama_model) + preflight.wsl_checks(cfg)
    for line in preflight.describe(checks):
        log(line)
    if preflight.failed(checks):
        return {"status": "blocked", "gguf": ""}
    config_path, count = write_inputs(cfg, user)
    if dry_run:
        dry_stats(cfg, os.path.join(run_dir(cfg), "train.jsonl"), log)
        log("Dry run: everything above is ready. " + ESTIMATE)
        return {"status": "dry_run", "gguf": ""}
    if not fresh and finished_model(cfg):
        log("An earlier training run is finished: reusing it (use --fresh to train again).")
        return {"status": "reused", "gguf": finished_model(cfg)}
    free_gpu(ollama_model, log)
    repo = wsl.quote(wsl.to_wsl_path(REPO_ROOT))
    log(f"Preparing the training tools inside WSL (first time only) ... {ESTIMATE}")
    setup = f"tr -d '\\r' < {repo}/ai_training/trainer/setup_env.sh | bash"   # tr: Windows git may add CR to the .sh file
    if wsl.stream(cfg, setup, log) != 0:
        return {"status": "setup_failed", "gguf": ""}
    cmd = f"cd {repo} && $HOME/ai_training_venv/bin/python -m ai_training.trainer.train --config {wsl.quote(wsl.to_wsl_path(config_path))}"
    log(f"Training on {count} proven traces ...")
    if wsl.stream(cfg, cmd, log) != 0:
        return {"status": "training_failed", "gguf": ""}
    gguf = finished_model(cfg)
    return {"status": "trained" if gguf else "no_model_file", "gguf": gguf}
