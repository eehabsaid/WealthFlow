"""QLoRA training on the proven traces (runs in WSL2, from the repo folder): python -m ai_training.trainer.train --config run_config.json

Loads the ORIGINAL model from disk in 4-bit, trains a small LoRA add-on on the assistant turns only, then merges and exports.
Everything GPU-related is in load_deps(), so the rest can be tested with fakes."""

from __future__ import annotations

import argparse
import json
import os
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


def text_tokenizer(processor):
    """The model loads with a processor (it also has a vision part); text work needs only its tokenizer."""
    return getattr(processor, "tokenizer", processor)


def sft_config(deps, cfg: dict, out_dir: str):
    fields = getattr(deps.SFTConfig, "__dataclass_fields__", {})
    length_key = "max_length" if "max_length" in fields else "max_seq_length"   # renamed between trl versions
    return deps.SFTConfig(dataset_text_field="text", per_device_train_batch_size=cfg["batch_size"], gradient_accumulation_steps=cfg["grad_accum"],
                          warmup_steps=5, num_train_epochs=cfg["epochs"], learning_rate=cfg["learning_rate"], logging_steps=1, optim="adamw_8bit",
                          weight_decay=0.001, lr_scheduler_type="linear", seed=3407, report_to="none", output_dir=os.path.join(out_dir, "checkpoints"),
                          **{length_key: cfg["max_seq_length"]})


def run(cfg: dict, deps=None, log=print) -> dict:
    deps = deps or load_deps()
    out_dir = cfg["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    log(f"Loading the base model (4-bit) from {cfg['base_model_dir']} ...")
    model, processor = deps.FastModel.from_pretrained(model_name=cfg["base_model_dir"], max_seq_length=cfg["max_seq_length"], load_in_4bit=True,
                                                      load_in_16bit=False, full_finetuning=False)
    tok = text_tokenizer(processor)
    texts, stats = render.render_file(cfg["train_file"], tok, cfg["max_seq_length"], cfg["enable_thinking"])
    render.write_stats(stats, out_dir)
    log(f"Training examples: {stats['kept']} of {stats['lines']} (too long: {stats['too_long']}, unreadable: {stats['unreadable']}, longest: {stats['max_tokens']} tokens)")
    if not texts:
        raise RuntimeError("no training example fits the length limit")
    user_marker, assistant_marker = render.find_markers(tok, cfg["enable_thinking"])
    model = deps.FastModel.get_peft_model(model, finetune_vision_layers=False, finetune_language_layers=True, finetune_attention_modules=True,
                                          finetune_mlp_modules=True, r=cfg["lora_rank"], lora_alpha=cfg["lora_alpha"], lora_dropout=0, bias="none",
                                          random_state=3407)
    trainer = deps.SFTTrainer(model=model, tokenizer=processor, train_dataset=deps.Dataset.from_list([{"text": t} for t in texts]),
                              args=sft_config(deps, cfg, out_dir))
    trainer = deps.train_on_responses_only(trainer, instruction_part=user_marker, response_part=assistant_marker)
    started = time.time()
    result = trainer.train()
    log(f"Training finished in {(time.time() - started) / 60:.0f} min, final loss {getattr(result, 'training_loss', 'n/a')}")
    files = export_gguf.save_all(model, processor, out_dir, cfg["gguf_quant"])
    summary = {**files, "examples": stats["kept"], "minutes": round((time.time() - started) / 60)}
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
