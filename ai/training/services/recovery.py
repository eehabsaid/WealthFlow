"""Validation, export, training, and registration for the isolated Recovery profile."""

from __future__ import annotations

from dataclasses import replace
from typing import Callable

from ai.training.services import evaluate, ollama_stage, pipeline, train_stage
from ai.training.services.config import load as load_config
from .recovery_data import export_dataset, format_report, validate_dataset, _append_replay  # noqa: F401
from .recovery_profile import load_profile, report_paths, resolve_path, _PROFILES_DIR, PROFILE_PATH, PROFILE_PATHS, SYSTEM_PROMPT, dataset_path  # noqa: F401


def run(stages: str | None = None, *, dry_run: bool = False, fresh: bool = False, username: str = "",
        log: Callable[[str], None] = print, profile_name: str = "recovery") -> dict:
    profile, cfg = load_profile(profile_name) if profile_name != "recovery" else load_profile()
    requested = set((stages or "validate,export,train,register,evaluate").split(","))
    allowed = {"validate", "export", "train", "register", "evaluate"}
    unknown = requested - allowed
    if unknown or not requested:
        raise ValueError(f"unknown Recovery stage(s): {', '.join(sorted(unknown or requested))}")

    result = {"paths": {}, "training": None, "registered": False}
    report = None
    exported = None
    if "validate" in requested:
        report = validate_dataset(profile)
        if not report["valid"]:
            raise ValueError(format_report(report))
        result["paths"].update(report_paths(profile))
    if "export" in requested:
        exported, report = export_dataset(profile)
        result["exported_dataset"] = exported
        result["paths"].update(report_paths(profile))
        log(f"Exported {report['examples']} validated examples to {exported}.")
    if "train" in requested:
        if exported is None:
            exported, report = export_dataset(profile)
            log(f"Validated and exported {report['examples']} examples to {exported}.")
        result["paths"].update(report_paths(profile))
        result["paths"]["training_dataset"] = exported
        result["training"] = train_stage.run_prepared(
            cfg, exported, report["examples"] + report.get("replay", 0), profile["base_ollama_model"],
            dry_run=dry_run, fresh=fresh, log=log,
        )
        reason = train_stage.explain(result["training"])
        if reason:
            log(reason)
    if "register" in requested and not dry_run:
        if not profile["register_with_ollama"]:
            raise RuntimeError("Recovery Ollama registration is disabled in profiles/recovery.json.")
        if result["training"] and result["training"].get("status") not in {"trained", "reused"}:
            raise RuntimeError(f"Recovery registration skipped because training ended with {result['training'].get('status')}.")
        exported_model = train_stage.finished_export(cfg)
        if not exported_model["gguf"] or not exported_model["mmproj"] or not exported_model["vision_assets"]:
            raise RuntimeError("Recovery model export is incomplete; run the Recovery train stage before register.")
        name = profile["ollama_model_name"]
        success = ollama_stage.register(
            profile["base_ollama_model"], exported_model["gguf_files"] or exported_model["gguf"],
            exported_model["mmproj"], name, train_stage.run_dir(cfg), log,
        )
        if not success:
            raise RuntimeError(f"Could not register the Recovery model as {name}.")
        result["registered"] = True
        result["model_name"] = name
        log(f"Recovery model registered in Ollama as {name}.")

    if "evaluate" in requested:
        user = pipeline.pick_user(username)
        comparison_model = profile.get("compare_model_name") or profile["base_ollama_model"]
        if comparison_model == profile["ollama_model_name"]:
            raise ValueError("Recovery comparison model and Recovery model name must be different.")
        evaluation_cfg = replace(load_config(), ollama_models_dir=cfg.ollama_models_dir)
        roles = [("WealthFlow", comparison_model), (profile.get("label", "Recovery"), profile["ollama_model_name"])]
        if dry_run:
            result["evaluation"] = evaluate.dry(
                user, evaluation_cfg, pipeline.current_model(), resolve_path(profile["reports_dir"]), log,
                model_roles=roles, benchmark_dir=pipeline.OUTPUT_DIR,
            )
        else:
            result["evaluation"] = evaluate.run(
                user, evaluation_cfg, evaluate.current_model(), out_dir=resolve_path(profile["reports_dir"]), log=log,
                model_roles=roles, benchmark_dir=pipeline.OUTPUT_DIR,
            )
        result["paths"].update(result["evaluation"].get("paths", {}))

    if report is None and "evaluate" not in requested:
        report = validate_dataset(profile)
    result["report"] = format_report(report) if report is not None else ""
    return result
