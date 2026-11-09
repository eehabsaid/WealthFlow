"""Coding-agent training, ONE command (phase 3): python scripts/agent_train.py [--stages dataset,train,evaluate] [--limit N] [--no-verify] [--dry-run] [--fresh]
dataset = verified examples from this repo's git history; train = coding-only fine-tune (WSL2 + GPU); evaluate = original vs new model on held-out real changes.
Settings: coding_agent/training.json and ai/training/config.json. It never switches the model in Settings."""

import argparse
import json
import os
import sys

import agent_cli
from core.models import AppSettings
from ai.services.coding.training import dataset, evaluate, stage

ROOT = agent_cli.ROOT  # importing agent_cli sets up Django


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stages", default="dataset,train,evaluate")
    ap.add_argument("--limit", type=int, default=0, help="only the newest N commits")
    ap.add_argument("--no-verify", action="store_true", help="count candidate changes only; run no tests, write no dataset")
    ap.add_argument("--dry-run", action="store_true", help="train stage: checks only, no training")
    ap.add_argument("--fresh", action="store_true")
    args = ap.parse_args(argv)
    stages = {s.strip() for s in args.stages.split(",") if s.strip()}
    cfg = stage.train_config()
    out_dir = os.path.join(cfg.work_dir, "coding")
    current = str(AppSettings.get("ai_model", "", user=None) or "")
    original, new_model = stage.names(current, cfg)
    log = lambda line: print(line, flush=True)  # noqa: E731
    files = {"train_file": os.path.join(out_dir, "coding_train.jsonl"), "held_out_file": os.path.join(out_dir, "coding_heldout.json")}
    if "dataset" in stages:
        result = dataset.build(args.limit, verify=not args.no_verify, log=log)
        log("Dataset: " + ", ".join(f"{k}={v}" for k, v in sorted(result["stats"].items())))
        if not args.no_verify:
            files = dataset.write(result, out_dir)
            log(f"Wrote {files['train']} training and {files['held_out']} held-out verified examples to {out_dir}")
    if "train" in stages:
        outcome = stage.run(files["train_file"], current, dry_run=args.dry_run, fresh=args.fresh, log=log)
        log(f"Training stage: {outcome['status']}")
        if outcome["status"] not in ("trained", "dry_run"):
            return 1
    if "evaluate" in stages:
        from ai.training.services import ollama_ctl, train_stage

        url = ollama_ctl.base_url()

        def restart(model):
            if not ollama_ctl.restart(cfg.ollama_models_dir, url, log):
                train_stage.free_gpu(model, log)

        try:
            with open(files["held_out_file"], encoding="utf-8") as fh:
                tasks = json.load(fh)
        except (OSError, ValueError):
            tasks = []
        outcome = evaluate.run((original, new_model), tasks, out_dir, lambda m, msgs, t: evaluate.chat(url, m, msgs, t), log, restart)
        log(outcome["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
