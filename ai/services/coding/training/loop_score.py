"""Scoring of one REAL agent run, and the decision between two models.

A row is read from what the agent itself logged in the working copy it ran in (coding_agent/tasks/<id>/ledger.json and events.jsonl): nothing is guessed from
the model's text. A task counts as DONE when
  qa     the agent finished with a final answer (status "answered") after using at least one tool, and every file path the answer cites exists in the repo;
  patch  the agent made a plan, the plan was executed, and the agent's own final checks (the project's verify_steps) said VERIFIED;
and in both cases no protected file was touched. A text-similarity number and the overlap with the files the recorded real answer cites are kept in the row for
the human reader only: they never decide anything. The decision is conservative: the new model must do clearly more of the same real tasks, lose nothing in
either kind, touch no protected file and not be much slower, on at least `eval_min_tasks` tasks."""

from __future__ import annotations

import json
import statistics
from difflib import SequenceMatcher
from pathlib import Path

from ai.dev_agent.core.project import Project
from ai.dev_agent.service import trajectory
from ai.services.coding.training import ledger_traj as traj
from ai.services.coding.training import ledger_traj_check as check


def task_folder(root) -> Path | None:
    """The one task the agent created in a fresh working copy (None when it never got as far as creating a ledger)."""
    base = Path(root) / "coding_agent" / "tasks"
    folders = sorted(p for p in base.iterdir() if (p / "ledger.json").is_file()) if base.is_dir() else []
    return folders[-1] if folders else None


def _why(row: dict, expected: str, got: str, data: dict) -> str:
    if row["timed_out"]:
        return "timed out"
    if got == expected:
        if row["protected_touches"]:
            return "touched protected files: " + ", ".join(row["protected_touches"])
        if expected == "qa" and not row["tool_calls"]:
            return "answered without reading anything"
        if expected == "qa" and row["cited_missing"]:
            return "the answer cites files that do not exist: " + ", ".join(row["cited_missing"][:4])
        return ""
    status = row["status"]
    if status == "stopped":
        return "stopped: " + (row["stop_reason"] or "no reason recorded")[:200]
    if expected == "patch" and status == "answered":
        return "answered in words instead of making a plan"
    if expected == "qa" and status in ("awaiting_approval", "completed"):
        return "proposed changes for a question"
    if status == "completed":
        final = next((v for v in reversed(data.get("verification") or []) if v["label"] == "final"), None)
        return "finished but the final checks did not say VERIFIED" + (f" ({final['results'][0]['status']}...)" if final and final["results"] else "")
    return f"ended as '{status}'"


def score_task(root, task: dict, run: dict) -> dict:
    """One row for one finished run. `task` = {task_id, kind, goal, answer}; `run` = {returncode, seconds, timed_out, tail}."""
    row = {"task_id": task["task_id"], "kind": task["kind"], "seconds": round(float(run["seconds"]), 1), "timed_out": bool(run["timed_out"]), "returncode": run["returncode"],
           "status": "no_task_folder", "success": False, "why": "", "stop_reason": "", "tool_calls": 0, "tool_errors": 0, "invalid_replies": 0, "tokens": 0,
           "protected_touches": [], "cited_missing": [], "path_overlap": None, "similarity": None, "answer": "", "folder": ""}
    folder = task_folder(root)
    try:
        data = json.loads((folder / "ledger.json").read_text(encoding="utf-8")) if folder else None
    except (OSError, ValueError):
        data = None
    if data is None:
        row["why"] = "timed out" if row["timed_out"] else f"no readable task folder (exit code {run['returncode']}): " + str(run.get("tail") or "")[-300:].strip()
        return row
    project, events = Project(root), trajectory.read_events(folder / "events.jsonl")
    phases = trajectory.phases(events)
    usage = data.get("usage") or {}
    row.update(status=str(data.get("status") or ""), stop_reason=str(data.get("stop_reason") or ""), answer=str(data.get("answer") or ""), folder=folder.name,
               tool_calls=sum(len(p["tools"]) for p in phases), tool_errors=sum(p["tool_errors"] for p in phases),
               invalid_replies=sum(1 for e in events if e.get("type") == "trace" and e.get("kind") == "message" and e.get("why") == "invalid_reply_nudge"),
               tokens=int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0),
               protected_touches=sorted(f for f in (data.get("files") or {}) if project.protected_reason(f)))
    if row["answer"]:
        row["cited_missing"] = check.cited_missing(project, row["answer"])
        row["similarity"] = round(SequenceMatcher(None, row["answer"].lower(), str(task.get("answer") or "").lower()).ratio(), 3)
        wanted = set(check.CITED.findall(str(task.get("answer") or "")))
        row["path_overlap"] = round(len(wanted & set(check.CITED.findall(row["answer"]))) / len(wanted), 2) if wanted else None
    got = traj.task_kind(data)
    row["why"] = _why(row, task["kind"], got, data)
    row["success"] = got == task["kind"] and not row["why"]
    return row


def summarize(model: str, rows: list[dict]) -> dict:
    def part(kind: str) -> dict:
        mine = [r for r in rows if r["kind"] == kind]
        return {"tasks": len(mine), "success": sum(1 for r in mine if r["success"])}

    done = sum(1 for r in rows if r["success"])
    return {"model": model, "tasks": len(rows), "success": done, "success_pct": round(100 * done / len(rows), 1) if rows else 0.0, "qa": part("qa"), "patch": part("patch"),
            "protected_touches": sum(1 for r in rows if r["protected_touches"]), "timeouts": sum(1 for r in rows if r["timed_out"]),
            "invalid_replies": sum(r["invalid_replies"] for r in rows), "median_seconds": round(statistics.median([r["seconds"] for r in rows]), 1) if rows else 0.0}


def verdict(old: dict, new: dict, cfg: dict) -> tuple[bool, str]:
    """(new model clearly better?, one sentence). Never True on too few tasks."""
    need = int(cfg.get("eval_min_tasks", 10))
    ran = min(old["tasks"], new["tasks"])
    if ran < need:
        return False, f"NOT ENOUGH TASKS: {ran} real tasks were run with both models (need {need}). Nothing is decided and nothing is switched."
    gain, reasons = new["success_pct"] - old["success_pct"], []
    if new["success"] <= old["success"] or gain < cfg["eval_min_gain_points"]:
        reasons.append(f"only {gain:+.1f} points more real tasks done (need {cfg['eval_min_gain_points']})")
    for kind in ("qa", "patch"):
        if new[kind]["success"] < old[kind]["success"]:
            reasons.append(f"worse on {kind} tasks ({new[kind]['success']} done against {old[kind]['success']})")
    if new["protected_touches"]:
        reasons.append("touched protected files")
    slower = 100 * (new["median_seconds"] - old["median_seconds"]) / old["median_seconds"] if old["median_seconds"] else 0.0
    if slower > cfg["eval_max_slower_percent"]:
        reasons.append(f"{slower:.0f}% slower (median seconds per task)")
    return (not reasons), ("NEW MODEL WINS on real agent-loop tasks" if not reasons else "NO WIN: " + "; ".join(reasons))
