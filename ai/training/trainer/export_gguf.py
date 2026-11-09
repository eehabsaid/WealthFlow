"""Export the trained adapter, merged GGUF, projector and original vision assets."""

from __future__ import annotations

import glob
import json
import os
import shutil

IMAGE_PROCESSOR_CONFIG_FILES = ("preprocessor_config.json", "image_processor_config.json")
PROCESSOR_CONFIG_FILES = (
    "processor_config.json",
    *IMAGE_PROCESSOR_CONFIG_FILES,
    "video_preprocessor_config.json",
)


def model_files(out_dir: str) -> list[str]:
    """GGUF model shards, excluding separately imported vision projectors."""
    found = glob.glob(os.path.join(out_dir, "gguf*", "**", "*.gguf"), recursive=True)
    return sorted(f for f in found if "mmproj" not in os.path.basename(f).lower())


def projector_files(out_dir: str) -> list[str]:
    """GGUF vision projectors emitted by Unsloth."""
    found = glob.glob(os.path.join(out_dir, "gguf*", "**", "*.gguf"), recursive=True)
    return sorted(f for f in found if "mmproj" in os.path.basename(f).lower())


def _save_vision_assets(processor, base_model_dir: str, out_dir: str) -> str:
    config_path = os.path.join(base_model_dir, "config.json")
    with open(config_path, encoding="utf-8") as fh:
        model_config = json.load(fh)
    if not isinstance(model_config.get("vision_config"), dict):
        raise RuntimeError(f"the base model config has no vision_config: {config_path}")
    if not callable(getattr(processor, "save_pretrained", None)):
        raise RuntimeError("the vision model processor cannot be saved")

    vision_dir = os.path.join(out_dir, "vision")
    os.makedirs(vision_dir, exist_ok=True)
    processor.save_pretrained(vision_dir)
    for name in ("config.json", "generation_config.json", *PROCESSOR_CONFIG_FILES):
        source = os.path.join(base_model_dir, name)
        if os.path.isfile(source):
            shutil.copy2(source, os.path.join(vision_dir, name))
    if not any(os.path.isfile(os.path.join(vision_dir, name)) for name in IMAGE_PROCESSOR_CONFIG_FILES):
        raise RuntimeError(f"the base image processor configuration was not preserved in {vision_dir}")
    if not any(os.path.isfile(os.path.join(vision_dir, name)) for name in ("tokenizer.json", "tokenizer.model", "vocab.json")):
        raise RuntimeError(f"the base tokenizer files were not preserved in {vision_dir}")
    return vision_dir


def save_all(model, processor, out_dir: str, quant: str, base_model_dir: str) -> dict:
    """Save the adapter, processor/config sidecar and Ollama-ready model/projector GGUFs."""
    adapter = os.path.join(out_dir, "adapter")
    model.save_pretrained(adapter)
    processor.save_pretrained(adapter)
    vision_assets = _save_vision_assets(processor, base_model_dir, out_dir)

    gguf_dir = os.path.join(out_dir, "gguf")
    model.save_pretrained_gguf(gguf_dir, processor, quantization_method=quant)
    files = model_files(out_dir)
    preferred = [path for path in files if quant.lower() in os.path.basename(path).lower()]
    if preferred:
        files = preferred
    if not files:
        raise RuntimeError(f"the GGUF export produced no model file under {out_dir}")

    projectors = projector_files(out_dir)
    if len(projectors) != 1:
        raise RuntimeError(f"expected exactly one GGUF vision projector under {out_dir}, found {len(projectors)}")
    return {
        "adapter": adapter,
        "gguf": max(files, key=os.path.getsize),
        "gguf_files": files,
        "mmproj": projectors[0],
        "vision_assets": vision_assets,
    }
