"""Run folders, training inputs and finished-export checks."""

from __future__ import annotations

import json
import os

from ai.training.services import export, wsl
from ai.training.services.config import TrainConfig


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
