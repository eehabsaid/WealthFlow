"""Training and test settings: ai_training/config.json (edit that file; the training keys are required, the model-test keys are optional)."""

from __future__ import annotations

import json
import os
from dataclasses import MISSING, asdict, dataclass, fields

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
    model_suffix: str         # new model name = the BASE model name + this suffix (a distinct name per training: never overwrites an earlier one)
    # Model test settings: optional in config.json (these are the defaults)
    ollama_models_dir: str = "D:\\ollama\\models"   # used only when the test restarts Ollama and OLLAMA_MODELS is not set
    original_model: str = ""       # optional: the Ollama name of the untouched base model ("" = the model in Settings minus any trained suffix)
    best_model: str = ""           # optional: the current best trained model to compare with ("" = base + first previous suffix)
    new_model: str = ""            # optional: exact name for the newly trained model ("" = base + model_suffix)
    previous_suffixes: tuple = ("-agent",)   # suffixes of earlier trained models: stripped to find the base model, and tested as "current best"
    eval_per_category: int = 8     # frozen test: questions per category (all four languages, round-robin)
    eval_seed: int = 2026          # same seed = same test questions (while the data is the same)
    eval_min_gain_points: int = 5  # the new model must score at least this many percentage points higher
    eval_max_slower_percent: int = 20  # ... and its median answer time may be at most this much longer

    def as_dict(self) -> dict:
        return asdict(self)


def load(path: str = CONFIG_PATH, **overrides) -> TrainConfig:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    wanted = {f.name for f in fields(TrainConfig)}
    required = {f.name for f in fields(TrainConfig) if f.default is MISSING}
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"{path} is missing: {', '.join(missing)}")
    raw = {k: v for k, v in raw.items() if k in wanted}
    raw.update({k: v for k, v in overrides.items() if v is not None})
    if "previous_suffixes" in raw:
        raw["previous_suffixes"] = tuple(raw["previous_suffixes"])
    return TrainConfig(**raw)
