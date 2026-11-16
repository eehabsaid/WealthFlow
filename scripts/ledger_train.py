"""Ledger-based coding_agent training, ONE command: python scripts/ledger_train.py [--stages extract,build,train,evaluate]
extract = scan coding_agent/tasks for completed+verified tasks and (re)write coding_agent/qa_review.jsonl and patch_review.jsonl for you to
approve/reject; build = merge the approved QA + patch rows into one deterministic train/held-out split (coding_agent/coding_agent_training.json
settings); train/evaluate = the same WSL trainer machinery as the other local models, continuing from your recovery model's own adapter and
registering the result as "<base>-coding_agent" - never "<something>-recovery...", and never switching the model in Settings. It never trains
without you having approved examples first (build refuses with nothing approved).

--mode loop trains the AGENT-LOOP model instead (the default mode is unchanged): extract = scan coding_agent/tasks for tasks with a full trace (events.jsonl)
and write coding_agent/traj_review.jsonl, one row per clean phase (multi-turn: system, user, assistant tool calls, tool results, final answer) for you to
approve/reject; build = the approved rows as one train/held-out split, held out by TASK; train = coding_agent/agent_loop_training.json, registers
"<base>-coding_agent"; evaluate = runs the REAL dev agent (python -m ai.dev_agent run) on the held-out tasks with the recovery model and with the new
model, in throw-away copies of the repo, and compares what each really got done (--max-eval-tasks N limits it). Nothing is ever switched in Settings."""

import argparse
import json
import os
import sys

import agent_cli
from ai.models import AISetting
from ai.services.coding.training import ledger_eval, ledger_review, ledger_stage, loop_eval, loop_stage
from ai.services.coding.training.evaluate import chat

ROOT = agent_cli.ROOT  # importing agent_cli sets up Django


def _restart(cfg, url):
    from ai.training.services import ollama_ctl, train_stage

    def restart(model):   # one model on the GPU at a time: restart Ollama (or free the GPU) before each model is tested
        if not ollama_ctl.restart(cfg.ollama_models_dir, url, lambda line: print(line, flush=True)):
            train_stage.free_gpu(model, lambda line: print(line, flush=True))

    return restart


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stages", default="extract,build,train,evaluate")
    ap.add_argument("--mode", choices=("single", "loop"), default="single", help="single = the QA + patch model (default); loop = the agent-loop model")
    ap.add_argument("--dry-run", action="store_true", help="train stage: checks only, no training")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--max-eval-tasks", type=int, default=0, help="loop evaluate: how many held-out tasks to run (0 = the eval_max_tasks of agent_loop_training.json)")
    args = ap.parse_args(argv)
    stages = {s.strip() for s in args.stages.split(",") if s.strip()}
    loop = args.mode == "loop"
    stage_mod = loop_stage if loop else ledger_stage
    folder = "coding_agent_loop" if loop else "coding_agent"
    cfg = stage_mod.train_config()
    out_dir = os.path.join(cfg.work_dir, folder)
    current = str(AISetting.get("ai_model", "", user=None) or "")
    best_model, new_model = stage_mod.names(current)
    log = lambda line: print(line, flush=True)  # noqa: E731
    files = {"train_file": os.path.join(out_dir, f"{folder}_train.jsonl"), "held_out_file": os.path.join(out_dir, f"{folder}_heldout.json")}
    if "extract" in stages:
        for kind in ("traj",) if loop else ("qa", "patch"):
            result = ledger_review.refresh(kind, log=log)
            log(f"{kind} candidates: " + ", ".join(f"{k}={v}" for k, v in sorted(result["stats"].items())))
    if "build" in stages:
        files = ledger_review.build_traj(out_dir, log=log) if loop else ledger_review.build_combined(out_dir, log=log)
        if not files["train"] and not files["held_out"]:
            if "train" in stages or "evaluate" in stages:
                log("Nothing approved yet: skipping train/evaluate.")
            stages -= {"train", "evaluate"}
    if "train" in stages:
        outcome = stage_mod.run(files["train_file"], current, dry_run=args.dry_run, fresh=args.fresh, log=log)
        log(f"Training stage: {outcome['status']}")
        if outcome["status"] not in ("trained", "dry_run"):
            return 1
    if "evaluate" in stages:
        from ai.training.services import ollama_ctl

        url = ollama_ctl.base_url()
        try:
            with open(files["held_out_file"], encoding="utf-8") as fh:
                held_out = json.load(fh)
        except (OSError, ValueError):
            held_out = []
        restart = _restart(cfg, url)
        if loop:
            limit = args.max_eval_tasks or int(loop_eval.settings(loop_eval.CONFIG_NAME).get("eval_max_tasks", 0))
            outcome = loop_eval.run((best_model, new_model), loop_eval.tasks_from_heldout(held_out, limit), out_dir, log=log, restart=restart)
        else:
            outcome = ledger_eval.run((best_model, new_model), held_out, out_dir, lambda m, msgs, t: chat(url, m, msgs, t), log, restart)
        log(outcome["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
