"""Ledger-based coding_agent training, ONE command: python scripts/ledger_train.py [--stages extract,build,train,evaluate]
extract = scan coding_agent/tasks for completed+verified tasks and (re)write coding_agent/qa_review.jsonl and patch_review.jsonl for you to
approve/reject; build = merge the approved QA + patch rows into one deterministic train/held-out split (coding_agent/coding_agent_training.json
settings); train/evaluate = the same WSL trainer machinery as the other local models, continuing from your recovery model's own adapter and
registering the result as "<base>-coding_agent" - never "<something>-recovery...", and never switching the model in Settings. It never trains
without you having approved examples first (build refuses with nothing approved)."""

import argparse
import json
import os
import sys

import agent_cli
from ai.models import AISetting
from ai.services.coding.training import ledger_eval, ledger_review, ledger_stage
from ai.services.coding.training.evaluate import chat

ROOT = agent_cli.ROOT  # importing agent_cli sets up Django


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stages", default="extract,build,train,evaluate")
    ap.add_argument("--dry-run", action="store_true", help="train stage: checks only, no training")
    ap.add_argument("--fresh", action="store_true")
    args = ap.parse_args(argv)
    stages = {s.strip() for s in args.stages.split(",") if s.strip()}
    cfg = ledger_stage.train_config()
    out_dir = os.path.join(cfg.work_dir, "coding_agent")
    current = str(AISetting.get("ai_model", "", user=None) or "")
    best_model, new_model = ledger_stage.names(current)
    log = lambda line: print(line, flush=True)  # noqa: E731
    files = {"train_file": os.path.join(out_dir, "coding_agent_train.jsonl"), "held_out_file": os.path.join(out_dir, "coding_agent_heldout.json")}
    if "extract" in stages:
        for kind in ("qa", "patch"):
            result = ledger_review.refresh(kind, log=log)
            log(f"{kind} candidates: " + ", ".join(f"{k}={v}" for k, v in sorted(result["stats"].items())))
    if "build" in stages:
        files = ledger_review.build_combined(out_dir, log=log)
        if not files["train"] and not files["held_out"]:
            if "train" in stages or "evaluate" in stages:
                log("Nothing approved yet: skipping train/evaluate.")
            stages -= {"train", "evaluate"}
    if "train" in stages:
        outcome = ledger_stage.run(files["train_file"], current, dry_run=args.dry_run, fresh=args.fresh, log=log)
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
        outcome = ledger_eval.run((best_model, new_model), tasks, out_dir, lambda m, msgs, t: chat(url, m, msgs, t), log, restart)
        log(outcome["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
