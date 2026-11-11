"""The training stage: checks -> data file -> (WSL) environment -> QLoRA training + export -> result. Resumes: a finished run is reused."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Callable

from ai.training.services import export, preflight, wsl
from ai.training.services.config import REPO_ROOT, TrainConfig

ESTIMATE = "Unmeasured estimate: several hours for a few hundred examples; the merge/export at the end needs lots of disk and memory."


def run_dir(cfg: TrainConfig) -> str:
    return cfg.run_dir_override or os.path.join(cfg.work_dir, "run" + cfg.model_suffix)   # one folder per model name: an earlier model's files are never reused or overwritten


def model_out_dir(cfg: TrainConfig) -> str:
    return cfg.out_dir_override or os.path.join(run_dir(cfg), "out")


def write_inputs(cfg: TrainConfig, user) -> tuple[str, int]:
    os.makedirs(run_dir(cfg), exist_ok=True)
    train_file = os.path.join(run_dir(cfg), "train.jsonl")
    count = export.export_jsonl(train_file, user)
    wsl_cfg = {**cfg.as_dict(), "base_model_dir": wsl.to_wsl_path(cfg.base_model_dir), "train_file": wsl.to_wsl_path(train_file),
               "out_dir": wsl.to_wsl_path(model_out_dir(cfg))}
    if cfg.checkpoint_dir_override:
        wsl_cfg["checkpoint_dir"] = wsl.to_wsl_path(cfg.checkpoint_dir_override)
    if cfg.initial_adapter_dir:
        wsl_cfg["initial_adapter_dir"] = wsl.to_wsl_path(cfg.initial_adapter_dir)
        wsl_cfg["initial_adapter_model"] = cfg.initial_adapter_model
    path = os.path.join(run_dir(cfg), "run_config.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(wsl_cfg, fh, indent=4)
    return path, count


def finished_export(cfg: TrainConfig) -> dict:
    """Local paths for a complete model/projector/processor export, allowing incomplete exports to be diagnosed."""
    out = model_out_dir(cfg)
    path = os.path.join(out, "result.json")
    result = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            result = json.load(fh)
    else:
        from ai.training.trainer import export_gguf

        if os.path.isdir(os.path.join(out, "adapter")):
            files = export_gguf.model_files(out)
            projectors = export_gguf.projector_files(out)
            if files:
                result["gguf_files"] = files
                result["gguf"] = max(files, key=os.path.getsize)
            if len(projectors) == 1:
                result["mmproj"] = projectors[0]
            result["vision_assets"] = os.path.join(out, "vision")

    raw_files = result.get("gguf_files") or ([result["gguf"]] if result.get("gguf") else [])
    gguf_files = [wsl.from_wsl_path(file) for file in raw_files]
    gguf_files = [file for file in gguf_files if os.path.isfile(file)]
    gguf = wsl.from_wsl_path(result.get("gguf", ""))
    if not gguf and gguf_files:
        gguf = max(gguf_files, key=os.path.getsize)
    mmproj = wsl.from_wsl_path(result.get("mmproj", ""))
    if not mmproj and not os.path.exists(path):
        from ai.training.trainer import export_gguf

        projectors = export_gguf.projector_files(out)
        if len(projectors) == 1:
            mmproj = projectors[0]
    if mmproj and not os.path.isfile(mmproj):
        mmproj = ""
    vision_assets = wsl.from_wsl_path(result.get("vision_assets", os.path.join(out, "vision")))
    if not _vision_assets_ready(vision_assets):
        vision_assets = ""
    return {"gguf": gguf if os.path.isfile(gguf) else "", "gguf_files": gguf_files, "mmproj": mmproj, "vision_assets": vision_assets}


def _vision_assets_ready(path: str) -> bool:
    if not path or not os.path.isdir(path) or not os.path.isfile(os.path.join(path, "config.json")):
        return False
    with open(os.path.join(path, "config.json"), encoding="utf-8") as fh:
        model_config = json.load(fh)
        has_image_processor = any(os.path.isfile(os.path.join(path, name)) for name in ("preprocessor_config.json", "image_processor_config.json"))
        has_tokenizer = any(os.path.isfile(os.path.join(path, name)) for name in ("tokenizer.json", "tokenizer.model", "vocab.json"))
        return isinstance(model_config.get("vision_config"), dict) and has_image_processor and has_tokenizer


def finished_model(cfg: TrainConfig) -> str:
    """Windows path of a fully exported model with its vision assets ("" if incomplete)."""
    export = finished_export(cfg)
    return export["gguf"] if export["mmproj"] and export["vision_assets"] else ""


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

        from ai.training.trainer import render

        tok = AutoTokenizer.from_pretrained(cfg.base_model_dir)
        tok = getattr(tok, "tokenizer", tok)
        render.find_markers(tok, cfg.enable_thinking)
        _, stats = render.render_file(train_file, tok, cfg.max_seq_length, cfg.enable_thinking)
        log(f"Length check: {stats['kept']} of {stats['lines']} examples fit {cfg.max_seq_length} tokens (too long: {stats['too_long']}, longest {stats['max_tokens']}).")
    except Exception as exc:   # transformers missing, tokenizer not loadable, template surprise: say it, do not stop
        log(f"Length check skipped: {type(exc).__name__}: {str(exc)[:160]}")


def _training_checks(cfg: TrainConfig, count: int, ollama_model: str, *, dry_run: bool,
                     count_name: str, log: Callable[[str], None]) -> list[preflight.Check]:
    checks = preflight.base_checks(cfg, count, ollama_model, count_name=count_name) + preflight.wsl_checks(cfg)
    if not dry_run and any(c.name == "WSL memory" and not c.ok for c in checks) and preflight.set_wsl_memory(cfg):
        log(f"Giving WSL {cfg.wsl_memory_gb} GB of memory in {preflight.wslconfig_path()} and restarting WSL ...")
        wsl.shutdown()
        checks = preflight.base_checks(cfg, count, ollama_model, count_name=count_name) + preflight.wsl_checks(cfg)
    for line in preflight.describe(checks):
        log(line)
    return checks


def run(cfg: TrainConfig, user, ollama_model: str, *, dry_run: bool = False, fresh: bool = False, log: Callable[[str], None] = print) -> dict:
    traces = len(export.kept_traces(user))
    checks = _training_checks(cfg, traces, ollama_model, dry_run=dry_run, count_name="proven traces", log=log)
    if preflight.failed(checks):
        return {"status": "blocked", "gguf": ""}
    config_path, count = write_inputs(cfg, user)
    train_file = os.path.join(run_dir(cfg), "train.jsonl")
    return _run_training(cfg, config_path, train_file, count, ollama_model, dry_run=dry_run, fresh=fresh, log=log)


def run_prepared(cfg: TrainConfig, train_file: str, count: int, ollama_model: str, *, dry_run: bool = False,
                 fresh: bool = False, log: Callable[[str], None] = print) -> dict:
    """Train a validated, pre-prepared JSONL dataset through the same QLoRA engine."""
    from ai.training.trainer.train import validate_initial_adapter

    validate_initial_adapter(cfg.as_dict())
    checks = _training_checks(cfg, count, ollama_model, dry_run=dry_run, count_name="validated examples", log=log)
    if preflight.failed(checks):
        return {"status": "blocked", "gguf": ""}
    if not os.path.isfile(train_file):
        raise FileNotFoundError(f"prepared training dataset does not exist: {train_file}")
    os.makedirs(run_dir(cfg), exist_ok=True)
    run_train_file = os.path.join(run_dir(cfg), "train.jsonl")
    if os.path.abspath(train_file) != os.path.abspath(run_train_file):
        shutil.copy2(train_file, run_train_file)
    wsl_cfg = {**cfg.as_dict(), "base_model_dir": wsl.to_wsl_path(cfg.base_model_dir),
               "train_file": wsl.to_wsl_path(run_train_file), "out_dir": wsl.to_wsl_path(model_out_dir(cfg))}
    if cfg.checkpoint_dir_override:
        wsl_cfg["checkpoint_dir"] = wsl.to_wsl_path(cfg.checkpoint_dir_override)
    if cfg.initial_adapter_dir:
        wsl_cfg["initial_adapter_dir"] = wsl.to_wsl_path(cfg.initial_adapter_dir)
        wsl_cfg["initial_adapter_model"] = cfg.initial_adapter_model
    config_path = os.path.join(run_dir(cfg), "run_config.json")
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(wsl_cfg, fh, indent=4)
    return _run_training(cfg, config_path, run_train_file, count, ollama_model, dry_run=dry_run, fresh=fresh, log=log,
                         count_name="validated examples")


def _run_training(cfg: TrainConfig, config_path: str, train_file: str, count: int, ollama_model: str, *,
                  dry_run: bool, fresh: bool, log: Callable[[str], None], count_name: str = "proven traces") -> dict:
    if dry_run:
        dry_stats(cfg, train_file, log)
        log("Dry run: everything above is ready. " + ESTIMATE)
        return {"status": "dry_run", "gguf": ""}
    previous = finished_export(cfg)
    finished_path = os.path.join(model_out_dir(cfg), "result.json")
    lineage_matches = not cfg.initial_adapter_dir
    if cfg.initial_adapter_dir and os.path.isfile(finished_path):
        with open(finished_path, encoding="utf-8") as fh:
            finished_info = json.load(fh)
        lineage_matches = (
            wsl.to_wsl_path(finished_info.get("initial_adapter_dir", "")) == wsl.to_wsl_path(cfg.initial_adapter_dir)
            and finished_info.get("initial_adapter_model") == cfg.initial_adapter_model
        )
    if not fresh and finished_model(cfg) and lineage_matches:
        log("An earlier training run from the configured starting checkpoint is finished: reusing it (use --fresh to train again).")
        return {"status": "reused", **previous}
    if not fresh and finished_model(cfg) and not lineage_matches:
        log("An earlier export has no matching starting-checkpoint record; training will run from the configured checkpoint.")
    free_gpu(ollama_model, log)
    repo = wsl.quote(wsl.to_wsl_path(REPO_ROOT))
    log(f"Preparing the training tools inside WSL (first time only) ... {ESTIMATE}")
    setup = f"tr -d '\\r' < {repo}/ai/training/trainer/setup_env.sh | bash"   # tr: Windows git may add CR to the .sh file
    code = wsl.stream(cfg, setup, log)
    if code != 0:
        return {"status": "setup_failed", "gguf": "", "exit_code": code}
    cmd = f"cd {repo} && $HOME/ai_training_venv/bin/python -m ai.training.trainer.train --config {wsl.quote(wsl.to_wsl_path(config_path))}"
    log(f"Training on {count} {count_name} ...")
    code = wsl.stream(cfg, cmd, log)
    if code != 0:
        return {"status": "training_failed", "gguf": "", "exit_code": code}
    exported = finished_export(cfg)
    if not exported["gguf"]:
        status = "no_model_file"
    elif not exported["mmproj"]:
        status = "no_vision_projector"
    elif not exported["vision_assets"]:
        status = "no_vision_assets"
    else:
        status = "trained"
    return {"status": status, **exported}


WHY = {
    "blocked": "A check above failed (see the [FAIL] line).",
    "setup_failed": "Preparing the training tools inside WSL failed (see the lines above).",
    "training_failed": "Training stopped before it finished. A stop with no error text almost always means WSL ran out of memory and Linux killed the process "
                       "(exit code 137), or WSL was shut down. Close heavy programs (browsers, VS Code, Ollama app) and run the same command again.",
    "no_model_file": "Training ended but no model file was made (see the lines above).",
    "no_vision_projector": "Training exported no GGUF vision projector (mmproj); the model was not registered.",
    "no_vision_assets": "Training did not preserve the base model's vision processor/config; the model was not registered.",
}


def explain(outcome: dict) -> str:
    """One plain sentence for a stage that did not finish; "" when it did."""
    status = outcome.get("status", "")
    if status not in WHY:
        return ""
    code = outcome.get("exit_code")
    return f"NOT FINISHED ({status}{', exit code ' + str(code) if code is not None else ''}): {WHY[status]}"
