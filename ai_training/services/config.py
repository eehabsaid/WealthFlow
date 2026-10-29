"""Training settings: ai_training/config.json (edit that file; every key is required, so nothing hides in code)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class TrainConfig:
    base_model_dir: str       # the ORIGINAL full-quality model folder (Hugging Face download)
    work_dir: str             # where data, the add-on and the finished model file are written (needs ~120 GB free)
    wsl_distro: str           # "" = the default WSL distribution
    min_traces: int           # fewer proven traces than this: no training
    min_free_gb: int
    wsl_memory_gb: int
    max_seq_length: int       # longest training example in tokens (longer ones are skipped and counted)
    lora_rank: int
    lora_alpha: int
    epochs: int
    learning_rate: float
    batch_size: int
    grad_accum: int
    enable_thinking: bool
    gguf_quant: str
    model_suffix: str         # new model name = the model set in Settings + this suffix

    def as_dict(self) -> dict:
        return asdict(self)


def load(path: str = CONFIG_PATH, **overrides) -> TrainConfig:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    wanted = {f.name for f in fields(TrainConfig)}
    missing = sorted(wanted - set(raw))
    if missing:
        raise ValueError(f"{path} is missing: {', '.join(missing)}")
    raw = {k: v for k, v in raw.items() if k in wanted}
    raw.update({k: v for k, v in overrides.items() if v is not None})
    return TrainConfig(**raw)
