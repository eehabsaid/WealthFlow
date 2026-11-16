"""Evaluation of the agent-loop model by running the REAL dev agent: for every held-out task and for each of the two models, a fresh throw-away copy of your
working tree is made, the copy's agent settings are pointed at the model, and `python -m ai.dev_agent --root <copy> run "<goal>"` is run exactly as you would run
it (the plan is approved automatically with --yes). The task is then scored from what the agent logged in that copy (loop_score.py) - plans, edits and the project's own checks
really run, nothing is judged by text similarity. Your repo, your task history and your Settings are never touched. Both models get the same tasks in the same
state; the full transcript of every run is kept. Nothing is ever switched: the report only says whether the new model is clearly better (loop_score.verdict).

The runner is a parameter, so the harness is tested with a scripted model; the default runner is the real command line."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from itertools import zip_longest
from pathlib import Path
from typing import Callable

from ai.services.coding import ROOT
from ai.services.coding.training import loop_report, loop_score, loop_snapshot, settings

CONFIG_NAME = "agent_loop_training.json"
TAIL = 20000


def tasks_from_heldout(held_out: list[dict], limit: int = 0) -> list[dict]:
    """One task per held-out task id ({task_id, kind, goal, answer}); with a limit, qa and patch tasks alternate so both kinds are tested."""
    found: dict[str, dict] = {}
    for ex in sorted(held_out, key=lambda e: e["task_id"]):
        found.setdefault(ex["task_id"], {"task_id": ex["task_id"], "kind": ex["task_kind"], "goal": ex["goal"], "answer": ex["answer"] if ex["task_kind"] == "qa" else ""})
    qa, patch = ([t for t in found.values() if t["kind"] == kind] for kind in ("qa", "patch"))
    ordered = [t for pair in zip_longest(qa, patch) for t in pair if t]
    return ordered[:limit] if limit else ordered


def run_cli(root, goal: str, timeout: int) -> dict:
    """The real command line, in `root`, with the plan approved automatically (--yes) and no terminal (stdin closed): a protected file or a command that needs
    approval is refused instead of waiting for an answer, so a batch never stops to ask. Never raises: a crash or a timeout is a result."""
    began, out = time.monotonic(), ""
    try:
        done = subprocess.run([sys.executable, "-m", "ai.dev_agent", "--root", str(root), "run", "--yes", goal], cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return {"returncode": done.returncode, "timed_out": False, "seconds": time.monotonic() - began, "tail": (done.stdout + done.stderr)[-TAIL:]}
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else exc.stdout) or ""
        return {"returncode": -1, "timed_out": True, "seconds": time.monotonic() - began, "tail": out[-TAIL:]}
    except OSError as exc:
        return {"returncode": -1, "timed_out": False, "seconds": time.monotonic() - began, "tail": f"could not start the agent: {exc}"}


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def run_task(model: str, task: dict, snapshot: Path, out_dir: Path, runner: Callable, timeout: int) -> dict:
    work = loop_snapshot.fresh_copy(snapshot, out_dir / "work" / _safe(model) / task["task_id"])
    try:
        loop_snapshot.pin_model(work, model)
        run = runner(work, task["goal"], timeout)
        row = loop_score.score_task(work, task, run)
        keep = out_dir / _safe(model) / task["task_id"]
        folder = loop_score.task_folder(work)
        if folder:
            shutil.copytree(folder, keep, dirs_exist_ok=True)
        keep.mkdir(parents=True, exist_ok=True)
        (keep / "run_output.txt").write_text(str(run.get("tail") or ""), encoding="utf-8")
        return row
    finally:
        loop_snapshot.remove(work)


def run(models: tuple[str, str], tasks: list[dict], out_dir: str, runner: Callable = run_cli, log: Callable[[str], None] = print, restart: Callable = lambda m: None,
        root=None, cfg: dict | None = None) -> dict:
    """Both models on every task; writes loop_eval_report.txt, loop_eval_results.json and loop_eval/<model>/<task>/ (the transcripts) into out_dir."""
    if not tasks:
        return {"status": "no_tasks", "win": False, "text": "No approved held-out trajectories: build the dataset first (python scripts/ledger_train.py --mode loop --stages extract,build)."}
    cfg = cfg or settings(CONFIG_NAME)
    out = Path(out_dir) / "loop_eval"
    info = loop_snapshot.snapshot(root or ROOT, out / "snapshot")
    log(f"Working copy of the repo: {info['files']} files" + ("" if info["git"] else " (this folder has no git history)"))
    rows: dict[str, list[dict]] = {}
    (out / "rows.jsonl").unlink(missing_ok=True)   # one line per finished run, written as it finishes; a new evaluation never reuses an old one
    try:
        for model in models:
            restart(model)
            rows[model] = []
            for number, task in enumerate(tasks, 1):
                row = run_task(model, task, out / "snapshot", out, runner, int(cfg["eval_task_timeout_s"]))
                rows[model].append(row)
                log(f"{model}: [{number}/{len(tasks)}] {task['task_id']} ({task['kind']}) -> " + ("DONE" if row["success"] else f"FAIL: {row['why'] or row['status']}") + f" in {row['seconds']}s")
                with open(out / "rows.jsonl", "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"model": model, **row}, ensure_ascii=False) + "\n")
    finally:
        loop_snapshot.remove(out / "snapshot")
        loop_snapshot.remove(out / "work")
    summaries = [loop_score.summarize(m, rows[m]) for m in models]
    won, text = loop_score.verdict(summaries[0], summaries[1], cfg)
    report = loop_report.report_text(summaries, rows, text, str(out))
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    Path(out_dir, "loop_eval_report.txt").write_text(report + "\n", encoding="utf-8")
    Path(out_dir, "loop_eval_results.json").write_text(json.dumps({"summaries": summaries, "rows": rows, "verdict": text}, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"status": "done", "win": won, "text": report, "summaries": summaries, "rows": rows}
