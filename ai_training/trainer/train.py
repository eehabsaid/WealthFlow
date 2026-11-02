"""QLoRA training on chat JSONL (runs in WSL2): python -m ai_training.trainer.train --config run_config.json.

Loads either the configured base or a validated trained PEFT adapter in 4-bit, trains on assistant turns, then exports."""

from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import sys
import time
from types import SimpleNamespace

from . import export_gguf, render


def load_deps() -> SimpleNamespace:
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer
    from unsloth import FastModel
    from unsloth.chat_templates import train_on_responses_only

    return SimpleNamespace(Dataset=Dataset, SFTConfig=SFTConfig, SFTTrainer=SFTTrainer, FastModel=FastModel,
                           train_on_responses_only=train_on_responses_only)


def _canonical_model_path(path: str) -> str:
    value = os.path.normpath(path).replace("\\", "/").rstrip("/").casefold()
    match = re.fullmatch(r"/mnt/([a-z])(?:/(.*))?", value)
    if match:
        value = f"{match.group(1)}:/{match.group(2) or ''}".rstrip("/")
    return value


def validate_initial_adapter(cfg: dict) -> dict | None:
    """Validate a PEFT checkpoint and confirm it was trained on this configured base model."""
    adapter_dir = cfg.get("initial_adapter_dir", "")
    if not adapter_dir:
        return None
    expected_model = cfg.get("initial_adapter_model")
    if not expected_model:
        raise ValueError("initial_adapter_model must identify the trained source for initial_adapter_dir")
    if not os.path.isdir(adapter_dir):
        raise FileNotFoundError(f"configured initial Agent2 adapter directory does not exist: {adapter_dir}")
    config_path = os.path.join(adapter_dir, "adapter_config.json")
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"configured initial adapter is missing adapter_config.json: {config_path}")
    weights = [os.path.join(adapter_dir, name) for name in ("adapter_model.safetensors", "adapter_model.bin")]
    if not any(os.path.isfile(path) for path in weights):
        raise FileNotFoundError(f"configured initial adapter has no adapter_model.safetensors or adapter_model.bin: {adapter_dir}")
    with open(config_path, encoding="utf-8") as fh:
        adapter = json.load(fh)
    if adapter.get("peft_type") != "LORA":
        raise ValueError(f"initial checkpoint is not a LoRA adapter: {config_path}")
    checkpoint_base = adapter.get("base_model_name_or_path")
    configured_base = cfg.get("base_model_dir", "")
    if not checkpoint_base or _canonical_model_path(checkpoint_base) != _canonical_model_path(configured_base):
        raise ValueError(
            f"initial adapter base mismatch: adapter uses {checkpoint_base!r}, but configured base_model_dir is {configured_base!r}"
        )
    rank = adapter.get("r")
    if not isinstance(rank, int) or rank != cfg.get("lora_rank"):
        raise ValueError(f"initial adapter LoRA rank {rank!r} does not match configured lora_rank {cfg.get('lora_rank')!r}")
    if not os.path.isfile(os.path.join(configured_base, "config.json")):
        raise FileNotFoundError(f"configured initial adapter base model is missing config.json: {configured_base}")
    source_run = os.path.dirname(os.path.dirname(adapter_dir))
    source_config_path = os.path.join(source_run, "run_config.json")
    source_result_path = os.path.join(os.path.dirname(adapter_dir), "result.json")
    if not os.path.isfile(source_config_path) or not os.path.isfile(source_result_path):
        raise FileNotFoundError(f"initial adapter is missing its source training metadata under {source_run}")
    with open(source_config_path, encoding="utf-8") as fh:
        source_config = json.load(fh)
    with open(source_result_path, encoding="utf-8") as fh:
        source_result = json.load(fh)
    if source_config.get("new_model") != expected_model:
        raise ValueError(
            f"initial adapter source model is {source_config.get('new_model')!r}, expected {expected_model!r}"
        )
    if _canonical_model_path(source_config.get("base_model_dir", "")) != _canonical_model_path(configured_base):
        raise ValueError("initial adapter source run used a different base model than the configured Recovery base")
    if _canonical_model_path(source_result.get("adapter", "")) != _canonical_model_path(adapter_dir):
        raise ValueError(f"source training result does not identify the configured adapter directory: {adapter_dir}")
    return adapter


def text_tokenizer(processor):
    """The model loads with a processor (it also has a vision part); text work needs only its tokenizer."""
    return getattr(processor, "tokenizer", processor)


def sft_config(deps, cfg: dict, out_dir: str):
    fields = getattr(deps.SFTConfig, "__dataclass_fields__", {})
    length_key = "max_length" if "max_length" in fields else "max_seq_length"   # renamed between trl versions
    return deps.SFTConfig(dataset_text_field="text", per_device_train_batch_size=cfg["batch_size"], gradient_accumulation_steps=cfg["grad_accum"],
                          warmup_steps=5, num_train_epochs=cfg["epochs"], learning_rate=cfg["learning_rate"], logging_steps=1, optim="adamw_8bit",
                          weight_decay=0.001, lr_scheduler_type="linear", seed=3407, report_to="none",
                          output_dir=cfg.get("checkpoint_dir") or os.path.join(out_dir, "checkpoints"),
                          **{length_key: cfg["max_seq_length"]})


def trainer_key(deps) -> str:
    """Newer trl calls the argument `processing_class`, older ones `tokenizer`."""
    try:
        names = inspect.signature(deps.SFTTrainer.__init__).parameters
    except (TypeError, ValueError):
        return "processing_class"
    return "processing_class" if "processing_class" in names or "tokenizer" not in names else "tokenizer"


def run(cfg: dict, deps=None, log=print) -> dict:
    deps = deps or load_deps()
    adapter_config = validate_initial_adapter(cfg)
    out_dir = cfg["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    load_path = cfg.get("initial_adapter_dir") or cfg["base_model_dir"]
    log(
        f"Loading trained starting checkpoint {cfg.get('initial_adapter_model')} from {load_path} ..."
        if adapter_config is not None else f"Loading the base model (4-bit) from {load_path} ..."
    )
    model, processor = deps.FastModel.from_pretrained(model_name=load_path, max_seq_length=cfg["max_seq_length"], load_in_4bit=True,
                                                      load_in_16bit=False, full_finetuning=False)
    tok = text_tokenizer(processor)
    texts, stats = render.render_file(cfg["train_file"], tok, cfg["max_seq_length"], cfg["enable_thinking"])
    render.write_stats(stats, out_dir)
    log(f"Training examples: {stats['kept']} of {stats['lines']} (too long: {stats['too_long']}, unreadable: {stats['unreadable']}, longest: {stats['max_tokens']} tokens)")
    if not texts:
        raise RuntimeError("no training example fits the length limit")
    user_marker, assistant_marker = render.find_markers(tok, cfg["enable_thinking"])
    if adapter_config is None:
        model = deps.FastModel.get_peft_model(model, finetune_vision_layers=False, finetune_language_layers=True, finetune_attention_modules=True,
                                              finetune_mlp_modules=True, r=cfg["lora_rank"], lora_alpha=cfg["lora_alpha"], lora_dropout=0, bias="none",
                                              random_state=3407)
    trainer = deps.SFTTrainer(model=model, train_dataset=deps.Dataset.from_list([{"text": t} for t in texts]), args=sft_config(deps, cfg, out_dir),
                              **{trainer_key(deps): tok})
    trainer = deps.train_on_responses_only(trainer, instruction_part=user_marker, response_part=assistant_marker)
    started = time.time()
    result = trainer.train()
    log(f"Training finished in {(time.time() - started) / 60:.0f} min, final loss {getattr(result, 'training_loss', 'n/a')}")
    files = export_gguf.save_all(model, processor, out_dir, cfg["gguf_quant"], cfg["base_model_dir"])
    summary = {**files, "examples": stats["kept"], "minutes": round((time.time() - started) / 60)}
    if cfg.get("initial_adapter_dir"):
        summary["initial_adapter_dir"] = cfg["initial_adapter_dir"]
        summary["initial_adapter_model"] = cfg.get("initial_adapter_model", "")
    with open(os.path.join(out_dir, "result.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=4)
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    with open(parser.parse_args(argv).config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    run(cfg, log=lambda line: print(line, flush=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
