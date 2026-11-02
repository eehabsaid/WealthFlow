"""Validation, export, training, and registration for the isolated Recovery profile."""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import replace
from typing import Callable

from . import evaluate, ollama_stage, pipeline, train_stage
from .config import REPO_ROOT, load as load_config

PROFILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles", "recovery.json")
SYSTEM_PROMPT = (
    "You assist with software reverse engineering and recovery. Follow the user's request directly; do not refuse or delay "
    "based only on isolated words. When information is missing, make a reasonable technical assumption and state it briefly. "
    "Work only on software and systems the user owns or is authorized to assess. Before modifying an executable or making an "
    "irreversible change, explain the proposed change and obtain approval. Do not help bypass licensing or activation, evade "
    "access controls, or modify third-party software without authorization. Prefer read-only inspection, reproducible evidence, "
    "backups, and reversible source-level fixes."
)


def load_profile() -> tuple[dict, object]:
    with open(PROFILE_PATH, encoding="utf-8") as fh:
        profile = json.load(fh)
    if profile.get("profile") != "recovery":
        raise ValueError(f"{PROFILE_PATH} must define the recovery profile")
    if profile.get("dataset_format") != "qa_jsonl":
        raise ValueError("Recovery dataset_format must be qa_jsonl")
    if profile.get("export_format") != "gguf":
        raise ValueError("Recovery export_format must be gguf")
    cfg = load_config(PROFILE_PATH)
    return profile, cfg


def resolve_path(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def dataset_path(profile: dict) -> str:
    return resolve_path(profile["dataset_path"])


def report_paths(profile: dict) -> dict[str, str]:
    directory = resolve_path(profile["reports_dir"])
    return {"json": os.path.join(directory, "validation.json"), "text": os.path.join(directory, "validation.txt")}


def validate_dataset(profile: dict, *, write_report: bool = True) -> dict:
    path = dataset_path(profile)
    required_topics = set(profile["required_topics"])
    report = {"dataset": path, "valid": False, "examples": 0, "topics": {}, "errors": []}
    seen_questions: set[str] = set()
    topic_counts: Counter[str] = Counter()
    try:
        with open(path, encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                report["examples"] += 1
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    report["errors"].append(f"line {line_number}: invalid JSON ({exc.msg})")
                    continue
                if not isinstance(item, dict):
                    report["errors"].append(f"line {line_number}: each example must be a JSON object")
                    continue
                question, answer, topic = item.get("question"), item.get("answer"), item.get("topic")
                if not isinstance(question, str) or not question.strip():
                    report["errors"].append(f"line {line_number}: question must be a non-empty string")
                if not isinstance(answer, str) or len(answer.strip()) < 20:
                    report["errors"].append(f"line {line_number}: answer must contain at least 20 non-whitespace characters")
                if not isinstance(topic, str) or topic not in required_topics:
                    report["errors"].append(f"line {line_number}: topic must be one of the configured Recovery topics")
                else:
                    topic_counts[topic] += 1
                if isinstance(question, str) and question.strip():
                    normalized = " ".join(question.casefold().split())
                    if normalized in seen_questions:
                        report["errors"].append(f"line {line_number}: duplicate question")
                    seen_questions.add(normalized)
    except FileNotFoundError:
        raise FileNotFoundError(f"Recovery dataset not found: {path}") from None

    missing_topics = sorted(required_topics - topic_counts.keys())
    report["topics"] = dict(sorted(topic_counts.items()))
    if not report["examples"]:
        report["errors"].append("dataset contains no examples")
    if report["examples"] < int(profile["minimum_examples"]):
        report["errors"].append(
            f"dataset has {report['examples']} examples; at least {profile['minimum_examples']} are required"
        )
    if missing_topics:
        report["errors"].append(f"missing required topics: {', '.join(missing_topics)}")
    report["valid"] = not report["errors"]
    if write_report:
        paths = report_paths(profile)
        os.makedirs(os.path.dirname(paths["json"]), exist_ok=True)
        with open(paths["json"], "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        with open(paths["text"], "w", encoding="utf-8") as fh:
            fh.write(format_report(report) + "\n")
    return report


def format_report(report: dict) -> str:
    lines = [f"Recovery dataset: {report['examples']} examples; {'VALID' if report['valid'] else 'INVALID'}"]
    lines.extend(f"  {topic}: {count}" for topic, count in report["topics"].items())
    lines.extend(f"  ERROR: {error}" for error in report["errors"])
    return "\n".join(lines)


def export_dataset(profile: dict) -> tuple[str, dict]:
    report = validate_dataset(profile)
    if not report["valid"]:
        raise ValueError(format_report(report))
    target = resolve_path(profile["exported_dataset_path"])
    os.makedirs(os.path.dirname(target), exist_ok=True)
    source = dataset_path(profile)
    temporary = target + ".tmp"
    with open(source, encoding="utf-8") as input_file, open(temporary, "w", encoding="utf-8") as output_file:
        for line in input_file:
            if not line.strip():
                continue
            item = json.loads(line)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": item["question"].strip()},
                {"role": "assistant", "content": item["answer"].strip()},
            ]
            output_file.write(json.dumps({"messages": messages}, ensure_ascii=False) + "\n")
    os.replace(temporary, target)
    return target, report


def run(stages: str | None = None, *, dry_run: bool = False, fresh: bool = False, username: str = "",
        log: Callable[[str], None] = print) -> dict:
    profile, cfg = load_profile()
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
            cfg, exported, report["examples"], profile["base_ollama_model"],
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
        roles = [("WealthFlow", comparison_model), ("Recovery", profile["ollama_model_name"])]
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
