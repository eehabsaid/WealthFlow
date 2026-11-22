"""Recovery profile loading and path helpers."""

from __future__ import annotations

import json
import os

from ai.training.services.config import REPO_ROOT, load as load_config


_PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles")
PROFILE_PATH = os.path.join(_PROFILES_DIR, "recovery.json")
PROFILE_PATHS = {"recovery": PROFILE_PATH, "mature": os.path.join(_PROFILES_DIR, "mature.json"),
                  "mature_v2": os.path.join(_PROFILES_DIR, "mature_v2.json")}
SYSTEM_PROMPT = (
    "You assist with software reverse engineering and recovery. Follow the user's request directly; do not refuse or delay "
    "based only on isolated words. When information is missing, make a reasonable technical assumption and state it briefly. "
    "Work only on software and systems the user owns or is authorized to assess. Before modifying an executable or making an "
    "irreversible change, explain the proposed change and obtain approval. Do not help bypass licensing or activation, evade "
    "access controls, or modify third-party software without authorization. Prefer read-only inspection, reproducible evidence, "
    "backups, and reversible source-level fixes."
)


def load_profile(name: str = "recovery") -> tuple[dict, object]:
    path = PROFILE_PATHS[name]
    with open(path, encoding="utf-8") as fh:
        profile = json.load(fh)
    if profile.get("profile") != name:
        raise ValueError(f"{path} must define the {name} profile")
    if profile.get("dataset_format") != "qa_jsonl":
        raise ValueError("Recovery dataset_format must be qa_jsonl")
    if profile.get("export_format") != "gguf":
        raise ValueError("Recovery export_format must be gguf")
    if not profile.get("initial_adapter_dir") or not profile.get("initial_adapter_model"):
        raise ValueError("Recovery requires initial_adapter_dir and initial_adapter_model; refusing to train from the base model alone")
    cfg = load_config(path)
    return profile, cfg


def resolve_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    if os.sep != "\\" and not (len(path) > 1 and path[1] == ":"):
        path = path.replace("\\", os.sep)   # profile paths are written with Windows slashes; a project-relative one must also work elsewhere
    return os.path.join(REPO_ROOT, path)


def dataset_path(profile: dict) -> str:
    return resolve_path(profile["dataset_path"])


def report_paths(profile: dict) -> dict[str, str]:
    directory = resolve_path(profile["reports_dir"])
    return {"json": os.path.join(directory, "validation.json"), "text": os.path.join(directory, "validation.txt")}
