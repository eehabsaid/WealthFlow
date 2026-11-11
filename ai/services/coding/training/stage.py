"""Coding-only fine-tuning, using the shared trainer's validated prepared-data path."""

from __future__ import annotations

from typing import Callable

from ai.services.coding.training import settings


def train_config():
    from ai.training.services import config

    options = settings()
    overrides = {"model_suffix": options["model_suffix"], "min_traces": options["min_examples"]}
    for key in ("initial_adapter_dir", "initial_adapter_model"):
        if options.get(key):
            overrides[key] = options[key]
    return config.load(**overrides)


def names(current_model: str, cfg) -> tuple[str, str]:
    """Return the untouched base model and the distinct coding model name."""
    from ai.training.services import ollama_stage

    original = ollama_stage.base_name(current_model, cfg)
    return original, ollama_stage.new_name(original, cfg.model_suffix)


def count_lines(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())
    except OSError:
        return 0


def run(train_file: str, current_model: str, *, dry_run: bool = False, fresh: bool = False,
        log: Callable[[str], None] = print) -> dict:
    from ai.training.services import ollama_stage, preflight, train_stage

    cfg, count = train_config(), count_lines(train_file)
    original, new_model = names(current_model, cfg)
    coding_check = preflight.Check(
        "verified coding examples", count >= cfg.min_traces, f"{count} (need {cfg.min_traces})",
        "This repo's history gives too few verified changes to teach a model. Keep adding small, tested commits and run the dataset stage again.",
    )
    for line in preflight.describe([coding_check]):
        log(line)
    if preflight.failed([coding_check]):
        return {"status": "blocked", "model": ""}

    # The shared path validates the starting adapter, converts every Windows path
    # (including initial_adapter_dir) for WSL, and checks checkpoint lineage before reuse.
    outcome = train_stage.run_prepared(
        cfg, train_file, count, original, dry_run=dry_run, fresh=fresh, log=log,
    )
    if outcome["status"] == "dry_run":
        return {"status": "dry_run", "model": new_model}
    if outcome["status"] not in ("trained", "reused"):
        return {"status": outcome["status"], "model": ""}

    exported = train_stage.finished_export(cfg)
    if not (exported["gguf"] and exported["mmproj"] and exported["vision_assets"]):
        return {"status": "incomplete_export", "model": ""}
    ok = ollama_stage.register(
        original, exported["gguf_files"] or [exported["gguf"]], exported["mmproj"], new_model,
        train_stage.run_dir(cfg), log,
    )
    return {"status": "trained" if ok else "register_failed", "model": new_model if ok else ""}
