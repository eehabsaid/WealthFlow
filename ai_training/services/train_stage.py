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
    return os.path.join(cfg.work_dir, "run" + cfg.model_suffix)   # one folder per model name: an earlier model's files are never reused or overwritten


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
    out = os.path.join(run_dir(cfg), "out")
    path = os.path.join(out, "result.json")
    if not os.path.exists(path):   # export finished but the result note was not written: use the model file it left
        from ai_training.trainer import export_gguf

        files = export_gguf.model_files(out)
        return max(files, key=os.path.getsize) if files and os.path.isdir(os.path.join(out, "adapter")) else ""
    with open(path, encoding="utf-8") as fh:
        gguf = wsl.from_wsl_path(json.load(fh).get("gguf", ""))
    return gguf if gguf and os.path.exists(gguf) else ""


def free_gpu(ollama_model: str, log: Callable[[str], None]) -> None:
    """Training needs the whole GPU: unload the model Ollama keeps in memory after the last question (it stays up to 30 minutes)."""
    try:
        # no pipes: if Ollama is closed, `ollama stop` may start the Ollama server, which would keep a captured pipe open and make this call hang for ever
        done = subprocess.run(["ollama", "stop", ollama_model], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
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
    code = wsl.stream(cfg, setup, log)
    if code != 0:
        return {"status": "setup_failed", "gguf": "", "exit_code": code}
    cmd = f"cd {repo} && $HOME/ai_training_venv/bin/python -m ai_training.trainer.train --config {wsl.quote(wsl.to_wsl_path(config_path))}"
    log(f"Training on {count} proven traces ...")
    code = wsl.stream(cfg, cmd, log)
    if code != 0:
        return {"status": "training_failed", "gguf": "", "exit_code": code}
    gguf = finished_model(cfg)
    return {"status": "trained" if gguf else "no_model_file", "gguf": gguf}


WHY = {
    "blocked": "A check above failed (see the [FAIL] line).",
    "setup_failed": "Preparing the training tools inside WSL failed (see the lines above).",
    "training_failed": "Training stopped before it finished. A stop with no error text almost always means WSL ran out of memory and Linux killed the process "
                       "(exit code 137), or WSL was shut down. Close heavy programs (browsers, VS Code, Ollama app) and run the same command again.",
    "no_model_file": "Training ended but no model file was made (see the lines above).",
}


def explain(outcome: dict) -> str:
    """One plain sentence for a stage that did not finish; "" when it did."""
    status = outcome.get("status", "")
    if status not in WHY:
        return ""
    code = outcome.get("exit_code")
    return f"NOT FINISHED ({status}{', exit code ' + str(code) if code is not None else ''}): {WHY[status]}"
