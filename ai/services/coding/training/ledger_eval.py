"""Evaluating the ledger-trained coding_agent model against recovery (your current best, per coding_agent/coding_agent_training.json) on its
own held-out examples - QA and patch together, since they were trained together. Patch examples are scored by code, the same way as the
git-history coding dataset (scoring.py): the model's patch is applied to a clean worktree and the real configured tests decide - but since a
ledger task is not tied to one commit, the clean worktree is git HEAD rather than a parent commit (so this only sees committed state; local,
uncommitted dev-agent changes are not reproduced - see ai/training/README.md). QA examples have no code-checkable ground truth, so they are
scored with a disclosed text-similarity proxy only and the full transcripts are written out for a human to actually judge; the combined
verdict is decided by the patch results alone, QA stays informational."""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
from difflib import SequenceMatcher
from typing import Callable

from ai.services.coding.config import protected_reason, test_module
from ai.services.coding.training import history, scoring, settings

CONFIG_NAME = "coding_agent_training.json"


def _prompt(example: dict) -> list[dict]:
    return example["messages"][:2]


def score_patch(example: dict, answer: str, timeout: int) -> dict:
    patch = scoring.extract_patch(answer)
    row = {"format_ok": bool(patch), "applies": False, "tests_pass": False, "protected_touch": False, "note": ""}
    if not patch:
        row["note"] = "no patch in the answer"
        return row
    touched = history.patch_files(patch)
    row["protected_touch"] = any(protected_reason(f) for f in touched)
    if row["protected_touch"]:
        row["note"] = "touches a protected file"
        return row
    with history.checkout("HEAD") as repo:
        row["applies"], row["note"] = history.apply_patch(repo, patch)
        if not row["applies"]:
            return row
        labels = sorted({m for f in example["files"] for m in [test_module(f)] if m})
        if not labels:
            row["note"] = "no Django test module is mapped to these files (test_areas in coding_agent/config.json); applied but not run"
            return row
        try:
            done = subprocess.run([sys.executable, "manage.py", "test", *labels], cwd=repo, capture_output=True, timeout=timeout)
            row["tests_pass"] = done.returncode == 0
        except (OSError, subprocess.SubprocessError):
            row["note"] = "could not run the mapped tests"
    return row


def score_qa(example: dict, answer: str) -> dict:
    """A rough text-overlap proxy against the agent's own recorded answer - not a correctness judgment; QA quality still needs a human to read
    the transcript (kept in full in the report)."""
    ratio = SequenceMatcher(None, answer.strip().lower(), example["answer"].strip().lower()).ratio() if answer.strip() else 0.0
    return {"format_ok": bool(answer.strip()), "similarity": round(ratio, 3)}


def run_model(model: str, tasks: list[dict], ask: Callable, cfg: dict, log: Callable[[str], None]) -> dict:
    """Runs one model on every held-out task (QA and patch mixed), scoring each by its own kind."""
    rows = []
    for ex in tasks:
        try:
            answer, secs = ask(model, _prompt(ex), cfg["eval_timeout_s"])
        except (OSError, ValueError) as exc:
            answer, secs = "", 0.0
            log(f"{model}: no answer for {ex['task_id']} ({type(exc).__name__})")
        row = (score_patch(ex, answer, cfg.get("verify_timeout_s", cfg["eval_timeout_s"])) if ex["kind"] == "patch" else score_qa(ex, answer))
        rows.append({"task_id": ex["task_id"], "kind": ex["kind"], "seconds": round(secs, 1), "answer": answer, **row})
        log(f"{model}: {ex['task_id']} ({ex['kind']}) " +
            (f"applies={row['applies']} tests_pass={row['tests_pass']}" if ex["kind"] == "patch" else f"similarity={row['similarity']}"))
    return {"model": model, "rows": rows, "qa": summarize([r for r in rows if r["kind"] == "qa"], "qa"), "patch": summarize([r for r in rows if r["kind"] == "patch"], "patch")}


def summarize(rows: list[dict], kind: str) -> dict:
    n = max(1, len(rows))
    count = lambda key: sum(1 for r in rows if r[key])  # noqa: E731
    out = {"tasks": len(rows), "format_ok": count("format_ok"), "median_seconds": round(statistics.median([r["seconds"] for r in rows]), 1) if rows else 0.0}
    if kind == "patch":
        out |= {"applies": count("applies"), "tests_pass": count("tests_pass"), "tests_pass_pct": round(100 * count("tests_pass") / n, 1), "protected_touches": count("protected_touch")}
    else:
        out |= {"avg_similarity": round(statistics.mean([r["similarity"] for r in rows]), 3) if rows else 0.0}
    return out


def verdict(old: dict, new: dict, cfg: dict) -> tuple[bool, str]:
    """Decided by the patch results alone - QA has no code-checkable ground truth, so it never decides a win on its own."""
    if new["patch"]["tasks"] == 0:
        return False, "No held-out patch examples: nothing to decide a win by code. Read the QA transcripts yourself; nothing is switched automatically."
    old_p, new_p = old["patch"], new["patch"]
    gain = new_p["tests_pass_pct"] - old_p["tests_pass_pct"]
    slower = 100 * (new_p["median_seconds"] - old_p["median_seconds"]) / old_p["median_seconds"] if old_p["median_seconds"] else 0.0
    reasons = []
    if gain < cfg["eval_min_gain_points"]:
        reasons.append(f"only {gain:+.1f} points more tests passing (need {cfg['eval_min_gain_points']})")
    if new_p["protected_touches"] > 0:
        reasons.append("touched protected files")
    if slower > cfg["eval_max_slower_percent"]:
        reasons.append(f"{slower:.0f}% slower")
    return (not reasons), ("NEW MODEL WINS on patch examples" if not reasons else "NO WIN: " + "; ".join(reasons))


def report_text(old: dict, new: dict, win: str) -> str:
    lines = [f"--- patch ({new['patch']['tasks']} held-out) ---"]
    head = f"{'model':34} {'tasks':>5} {'tests pass':>10} {'applies':>8} {'format':>7} {'protected':>9} {'median s':>9}"
    line = lambda r: f"{r['model']:34} {r['patch']['tasks']:>5} {r['patch'].get('tests_pass_pct', 0):>9}% {r['patch'].get('applies', 0):>8} {r['patch']['format_ok']:>7} {r['patch'].get('protected_touches', 0):>9} {r['patch']['median_seconds']:>9}"  # noqa: E731
    lines += [head, line(old), line(new), "", win, "",
              "Evaluated on git HEAD, not the task's own moment in time: local uncommitted dev-agent changes are not reproduced here. Nothing was switched.",
              "", f"--- qa ({new['qa']['tasks']} held-out, similarity is only a rough proxy - read the transcripts) ---",
              f"{'model':34} {'tasks':>5} {'answered':>9} {'avg similarity':>15} {'median s':>9}"]
    for r in (old, new):
        lines.append(f"{r['model']:34} {r['qa']['tasks']:>5} {r['qa']['format_ok']:>9} {r['qa'].get('avg_similarity', 0):>15} {r['qa']['median_seconds']:>9}")
    lines.append("")
    for r in new["rows"]:
        if r["kind"] == "qa":
            lines.append(f"--- {r['task_id']} (similarity {r['similarity']}) ---\nNEW ANSWER: {r['answer'][:800]}\n")
    return "\n".join(lines)


def run(models: tuple[str, str], tasks: list[dict], out_dir: str, ask: Callable, log: Callable[[str], None] = print, restart: Callable = lambda m: None) -> dict:
    cfg = settings(CONFIG_NAME)
    if not tasks:
        return {"status": "no_tasks", "win": False, "text": "No approved held-out examples: build the dataset first (python scripts/ledger_train.py --stages extract,build)."}
    results = []
    for model in models:
        restart(model)
        results.append(run_model(model, tasks, ask, cfg, log))
    won, text = verdict(results[0], results[1], cfg)
    report = report_text(results[0], results[1], text)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "coding_agent_eval_report.txt"), "w", encoding="utf-8") as fh:
        fh.write(report + "\n")
    with open(os.path.join(out_dir, "coding_agent_eval_results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
    return {"status": "done", "win": won, "text": report, "results": results}
