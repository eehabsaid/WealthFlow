"""Point 11: the original model and the coding fine-tune answer the SAME held-out real changes; every answer is scored by code (scoring.py).
Ollama is restarted before each model (a clean GPU, as in the business model test). Nothing is switched: the report only says whether the new model
beat the old one by the margin in coding_agent/training.json. The thresholds are settings, not code."""

from __future__ import annotations

import json
import os
import statistics
import time
import urllib.request
from typing import Callable

from ai.services.coding.training import scoring, settings


def chat(url: str, model: str, messages: list[dict], timeout: int) -> tuple[str, float]:
    """(answer text, seconds) from a local Ollama; temperature 0 so the same question gets the same answer."""
    body = json.dumps({"model": model, "messages": messages, "stream": False, "think": False, "options": {"temperature": 0, "num_predict": 1500}}).encode()
    started = time.monotonic()
    req = urllib.request.Request(url + "/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        data = json.loads(res.read().decode("utf-8"))
    return str((data.get("message") or {}).get("content") or ""), time.monotonic() - started


def _prompt(example: dict) -> list[dict]:
    return example["messages"][:2]   # system + user; the assistant turn is the answer being tested


def run_model(model: str, tasks: list[dict], bases: dict, ask: Callable, cfg: dict, log: Callable[[str], None]) -> dict:
    rows = []
    for ex in tasks:
        try:
            answer, secs = ask(model, _prompt(ex), cfg["eval_timeout_s"])
        except (OSError, ValueError) as exc:
            answer, secs = "", 0.0
            log(f"{model}: no answer for {ex['sha'][:8]} ({type(exc).__name__})")
        row = scoring.score(ex, answer, cfg["verify_timeout_s"], bases[ex["sha"]], cfg["eval_regression"])
        rows.append({"sha": ex["sha"], "seconds": round(secs, 1), **row})
        log(f"{model}: {ex['sha'][:8]} applies={row['applies']} correct={row['correct']} regression={row['regression']}")
    return {"model": model, "rows": rows, **summarize(rows)}


def summarize(rows: list[dict]) -> dict:
    n = max(1, len(rows))
    count = lambda key: sum(1 for r in rows if r[key])  # noqa: E731
    return {"tasks": len(rows), "correct": count("correct"), "correct_pct": round(100 * count("correct") / n, 1), "applies": count("applies"),
            "format_ok": count("format_ok"), "regressions": count("regression"), "protected_touches": count("protected_touch"),
            "median_seconds": round(statistics.median([r["seconds"] for r in rows]), 1) if rows else 0.0}


def verdict(old: dict, new: dict, cfg: dict) -> tuple[bool, str]:
    """The new model wins only if it is clearly more correct, no more regressions, touches no protected file, and is not much slower."""
    gain = new["correct_pct"] - old["correct_pct"]
    slower = 100 * (new["median_seconds"] - old["median_seconds"]) / old["median_seconds"] if old["median_seconds"] else 0.0
    reasons = []
    if gain < cfg["eval_min_gain_points"]:
        reasons.append(f"only {gain:+.1f} points more correct (need {cfg['eval_min_gain_points']})")
    if new["regressions"] > old["regressions"]:
        reasons.append("more regressions")
    if new["protected_touches"] > 0:
        reasons.append("touched protected files")
    if slower > cfg["eval_max_slower_percent"]:
        reasons.append(f"{slower:.0f}% slower")
    return (not reasons), ("NEW MODEL WINS" if not reasons else "NO WIN: " + "; ".join(reasons))


def report_text(old: dict, new: dict, win: str) -> str:
    head = f"{'model':34} {'tasks':>5} {'correct':>8} {'applies':>8} {'format':>7} {'regress':>8} {'protected':>9} {'median s':>9}"
    line = lambda r: f"{r['model']:34} {r['tasks']:>5} {r['correct_pct']:>7}% {r['applies']:>8} {r['format_ok']:>7} {r['regressions']:>8} {r['protected_touches']:>9} {r['median_seconds']:>9}"  # noqa: E731
    note = ("'format' = answers that contain a patch (the closest measure of tool/format use for single-answer coding). 'regress' = area tests that passed "
            "before the patch and fail after it. Few tasks mean a large uncertainty: one task is worth 100/tasks points. Nothing was switched.")
    return "\n".join([head, line(old), line(new), "", win, "", note])


def run(models: tuple[str, str], tasks: list[dict], out_dir: str, ask: Callable, log: Callable[[str], None] = print, restart: Callable = lambda m: None) -> dict:
    cfg = settings()
    if not tasks:
        return {"status": "no_tasks", "win": False, "text": "No verified held-out change: build the dataset first (python scripts/agent_train.py --stages dataset)."}
    log("Measuring which area tests already pass on each parent commit (so a regression is never blamed on a model for a failing area) ...")
    bases = {ex["sha"]: scoring.baseline_ok(ex, cfg["verify_timeout_s"]) if cfg["eval_regression"] else None for ex in tasks}
    results = []
    for model in models:
        restart(model)
        results.append(run_model(model, tasks, bases, ask, cfg, log))
    won, text = verdict(results[0], results[1], cfg)
    report = report_text(results[0], results[1], text)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "coding_eval_report.txt"), "w", encoding="utf-8") as fh:
        fh.write(report + "\n")
    with open(os.path.join(out_dir, "coding_eval_results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
    return {"status": "done", "win": won, "text": report, "results": results}
