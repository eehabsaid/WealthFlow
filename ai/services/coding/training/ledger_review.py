"""Human review of ledger-based candidates, file-based: `refresh()` (re)writes coding_agent/<kind>_review.jsonl with one row per candidate,
decision defaulting to "pending" and kept across reruns once set; `build()` reads that file and turns the "approved" rows, and only those,
into a deterministic train/held-out split plus a report. A rejected or still-pending row never reaches a dataset - this file IS the gate."""

from __future__ import annotations

import json
import os
from collections import Counter

from ai.services.coding import AGENT_DIR
from ai.services.coding.training import ledger_examples as le

DECISIONS = ("pending", "approved", "rejected")


def review_path(kind: str) -> str:
    return str(AGENT_DIR / f"{kind}_review.jsonl")


def _row(example: dict, decision: str, notes: str) -> dict:
    return {"task_id": example["task_id"], "kind": example["kind"], "decision": decision, "notes": notes, "redactions": example["redactions"], "example": example}


def load_rows(kind: str) -> dict[str, dict]:
    """{task_id: row} of whatever is currently in the review file, or {} if it does not exist yet."""
    path = review_path(kind)
    if not os.path.isfile(path):
        return {}
    rows = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                rows[row["task_id"]] = row
    return rows


def write_rows(kind: str, rows: dict[str, dict]) -> str:
    path = review_path(kind)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for task_id in sorted(rows):
            fh.write(json.dumps(rows[task_id], ensure_ascii=False) + "\n")
    return path


def refresh(kind: str, project_=None, log=print) -> dict:
    """Re-extracts candidates and rewrites the review file: a task seen before keeps its decision and notes; a newly-qualifying task is added as
    "pending"; a task that no longer qualifies (e.g. the owner rejected the agent's plan after review, or it was re-run) is dropped."""
    result = le.extract(kind, project_)
    existing = load_rows(kind)
    rows = {}
    for example in result["candidates"]:
        old = existing.get(example["task_id"])
        decision, notes = (old["decision"], old.get("notes", "")) if old else ("pending", "")
        rows[example["task_id"]] = _row(example, decision, notes)
    dropped_ids = set(existing) - set(rows)
    path = write_rows(kind, rows)
    counts = Counter(r["decision"] for r in rows.values())
    log(f"{kind}: {len(rows)} candidate(s) in {path} ({counts['pending']} pending, {counts['approved']} approved, {counts['rejected']} rejected" +
        (f", {len(dropped_ids)} no longer qualify and were dropped" if dropped_ids else "") + ")")
    return {"path": path, "stats": result["stats"], "decisions": dict(counts), "dropped": sorted(dropped_ids)}


def approved_examples(kind: str) -> list[dict]:
    rows = load_rows(kind)
    bad = [row["decision"] for row in rows.values() if row["decision"] not in DECISIONS]
    if bad:
        raise ValueError(f"{review_path(kind)} has an unknown decision value: {bad[0]!r} (expected one of {DECISIONS})")
    return [row["example"] for row in rows.values() if row["decision"] == "approved"]


def write_dataset(label: str, examples: list[dict], out_dir: str) -> dict:
    """Deterministic held-out split (no leakage: the same task id is always on the same side, each example held out on its own kind's cadence)
    and the two dataset files + a stats report. `label` only names the output files - `examples` may mix "qa" and "patch" kinds."""
    train, held_out = [], []
    for ex in sorted(examples, key=lambda e: e["task_id"]):
        (held_out if le.held_out(ex["task_id"], le.config(ex["kind"])) else train).append(ex)
    os.makedirs(out_dir, exist_ok=True)
    train_file = os.path.join(out_dir, f"{label}_train.jsonl")
    with open(train_file, "w", encoding="utf-8") as fh:
        for ex in train:
            fh.write(json.dumps({"messages": ex["messages"]}, ensure_ascii=False) + "\n")
    held_file = os.path.join(out_dir, f"{label}_heldout.json")
    with open(held_file, "w", encoding="utf-8") as fh:
        json.dump(held_out, fh, ensure_ascii=False, indent=1)
    by_kind = Counter(ex["kind"] for ex in examples)
    stats = Counter({"approved": len(examples), "train": len(train), "held_out": len(held_out),
                      "avg_assistant_chars": (sum(len(e["messages"][2]["content"]) for e in examples) // len(examples)) if examples else 0})
    stats.update({f"approved_{k}": n for k, n in by_kind.items()})
    report = os.path.join(out_dir, f"{label}_dataset_report.txt")
    with open(report, "w", encoding="utf-8") as fh:
        fh.write("\n".join(f"{k}: {v}" for k, v in sorted(stats.items())) + "\n")
    return {"train_file": train_file, "held_out_file": held_file, "report": report, "train": len(train), "held_out": len(held_out)}


def build(kind: str, out_dir: str, log=print) -> dict:
    """Single-kind build (for inspecting one example type on its own, e.g. while reviewing); the real training dataset is build_combined()."""
    examples = approved_examples(kind)
    if not examples:
        log(f"{kind}: no approved examples yet - review {review_path(kind)} and set decision to \"approved\" for the ones to train on.")
        return {"train_file": "", "held_out_file": "", "report": "", "train": 0, "held_out": 0}
    result = write_dataset(kind, examples, out_dir)
    log(f"{kind}: wrote {result['train']} training and {result['held_out']} held-out approved examples to {out_dir}")
    return result


def build_combined(out_dir: str, log=print) -> dict:
    """The real coding_agent dataset: every approved QA example plus every approved patch example, in one train/held-out split. Nothing
    rejected or still pending in either review file ever reaches this."""
    examples = approved_examples("qa") + approved_examples("patch")
    if not examples:
        log("coding_agent: no approved examples yet - review coding_agent/qa_review.jsonl and coding_agent/patch_review.jsonl and set "
            "decision to \"approved\" for the ones to train on.")
        return {"train_file": "", "held_out_file": "", "report": "", "train": 0, "held_out": 0}
    result = write_dataset("coding_agent", examples, out_dir)
    log(f"coding_agent: wrote {result['train']} training and {result['held_out']} held-out approved examples "
        f"({sum(1 for e in examples if e['kind'] == 'qa')} qa + {sum(1 for e in examples if e['kind'] == 'patch')} patch) to {out_dir}")
    return result
