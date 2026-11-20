"""Multi-turn trajectory examples for the dev agent's REAL loop, built only from what a task actually logged (coding_agent/tasks/<id>/events.jsonl, written by
the agent itself since the trace upgrade): the system prompt, the first user message, every assistant reply and every tool result, in the exact text format the
agent sends to the Ollama provider. One example = one clean phase (planning, one work package, one fix attempt) of a task that ended `answered`, or `completed`
and VERIFIED. Nothing is rewritten and nothing is invented: a phase that needed a nudge, had its history trimmed, was stopped, or whose first check failed is
not an example. Each example is then checked against the repo (ledger_traj_check) and goes into coding_agent/traj_review.jsonl for you to approve or reject."""

from __future__ import annotations

import hashlib
import re
from collections import Counter

from ai.dev_agent.core import redact
from ai.dev_agent.core.project import Project
from ai.dev_agent.engine import verify
from ai.dev_agent.engine.protocol import parse_reply
from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.service import trajectory
from ai.services.coding.training import ledger_examples as le
from ai.services.coding.training import ledger_traj_check as check

FIX = re.compile(r"fix (.+) #(\d+)$")


def task_kind(data: dict) -> str:
    """'qa' (answered), 'patch' (completed and the final checks said VERIFIED), '' for anything else - a task that did not finish well teaches nothing."""
    if data.get("status") == "answered":
        return "qa"
    final = next((v for v in reversed(data.get("verification") or []) if v["label"] == "final"), None)
    return "patch" if data.get("status") == "completed" and final and verify.overall(final["results"]) == "VERIFIED" else ""


def _failed_first(data: dict, label: str) -> bool:
    first = next((v for v in data.get("verification") or [] if v["label"] == label), None)
    return bool(first) and any(r["status"] == "FAILED" for r in first["results"])


def _skip_reason(phase: dict, phases: list[dict], data: dict, kind: str, cfg: dict) -> str:
    """Why this phase is not an example ('' = it is eligible for the checks)."""
    if not phase["clean"]:
        return "phase_not_clean"
    if phase["images"]:
        return "images"
    label, fix = phase["label"], FIX.match(phase["label"])
    if label == "plan":
        if any(p["label"] == "plan" for p in phases[phase["index"] + 1:]):
            return "plan_rejected"   # a later plan phase replaced it
    elif label.startswith("package "):
        if kind != "patch":
            return "package_of_unfinished_task"
        only = sum(1 for p in phases if p["label"].startswith("package ")) == 1   # one package: its checks are the "final" ones
        if _failed_first(data, label.split(" ", 1)[1]) or (only and _failed_first(data, "final")):
            return "package_failed_first_check"
    elif fix:
        rounds = [int(m.group(2)) for p in phases if (m := FIX.match(p["label"])) and m.group(1) == fix.group(1)]
        if kind != "patch" or int(fix.group(2)) != max(rounds):
            return "fix_not_the_last_round"
    else:
        return "unknown_phase"
    if sum(1 for tool_ in phase["tools"] if tool_) < cfg.get("min_tool_calls", 1):
        return "too_few_tool_calls"
    return "too_many_tool_errors" if phase["tool_errors"] > cfg.get("max_tool_errors", 2) else ""


def _final_text(messages: list[dict]) -> str:
    action = parse_reply(messages[-1]["content"])
    return str(action.payload.get("summary") or "") if action.kind == "plan" and isinstance(action.payload, dict) else str(action.payload or "")


def example_from(project: Project, ledger_data: dict, phase: dict, kind: str, cfg: dict, history: list[dict] | None = None) -> tuple[dict | None, str]:
    """(example, '') or (None, why not). `phase` comes from trajectory.phases(); the checks run against the repo as it is now. `history` = the tool results
    of every phase of the task (a file a later package edited is still the task's own state)."""
    messages, hits = [], 0
    for message in trajectory.conversation(phase):
        text, n = redact.redact(message["content"], pii=cfg.get("redact_patterns", True))
        messages.append({"role": message["role"], "content": text})
        hits += n
    problems = check.replay(messages)
    if problems:
        return None, "no_replay"
    tokens = sum(len(m["content"]) for m in messages) / max(0.5, float(cfg.get("chars_per_token", 3.2)))
    if tokens > cfg.get("max_seq_tokens", 8192):
        return None, "too_long_for_trainer"
    if check.protected_writes(project, phase["results"]):
        return None, "protected_file"
    repo = check.repo_check(project, phase["results"], history)
    plan_problems = check.plan_check(project, parse_reply(messages[-1]["content"]).payload, ledger_data.get("files")) if phase["ended"] == "plan" else []
    if plan_problems:
        return None, "plan_stale"
    if cfg.get("require_repo_match", True) and not check.repo_matches(repo):
        return None, "repo_changed"
    answer = _final_text(messages)
    checks = {"replay": "ok", "repo": repo, "cited_missing": check.cited_missing(project, answer) if kind == "qa" else [], "tool_errors": phase["tool_errors"],
              "plan": "still valid" if phase["ended"] == "plan" else "n/a"}
    example = {"task_id": ledger_data["id"], "key": f"{ledger_data['id']}#{phase['index']}", "kind": "traj", "task_kind": kind, "label": phase["label"],
               "goal": str(ledger_data.get("goal") or "").strip(), "steps": phase["steps"], "tools": phase["tools"], "answer": answer, "est_tokens": int(tokens),
               "usage": phase["usage"], "checks": checks, "messages": messages, "redactions": hits + phase["redactions"]}
    return example, ""


def extract(project_: Project | None = None) -> dict:
    """{"candidates": [...], "stats": Counter}, like ledger_examples.extract. Every finished task with a trace is looked at; nothing is written here."""
    cfg, proj, stats, found = le.config("traj"), project_ or le.project(), Counter(), []
    for task_id in Ledger.list_ids(proj):
        stats["tasks"] += 1
        try:
            ledger = Ledger.load(proj, task_id)
        except FileNotFoundError:
            stats["dropped:unreadable"] += 1
            continue
        kind = task_kind(ledger.data)
        phases = trajectory.phases(trajectory.read_events(ledger.dir / "events.jsonl"))
        if not phases:
            stats["dropped:task_without_trace"] += 1
            continue
        if not kind:
            stats["dropped:task_not_finished_well"] += 1
            continue
        stats["tasks_with_trace"] += 1
        history = [row for phase in phases for row in phase["results"]]
        for phase in phases:
            stats["phases"] += 1
            why = _skip_reason(phase, phases, ledger.data, kind, cfg)
            example, why = (None, why) if why else example_from(proj, ledger.data, phase, kind, cfg, history)
            if example is None:
                stats["dropped:" + why] += 1
            else:
                found.append(example)
    seen, kept = set(), []
    for example in sorted(found, key=lambda e: e["key"]):
        fingerprint = hashlib.sha1(" ".join((example["goal"] + "\n" + example["messages"][-1]["content"]).split()).lower().encode("utf-8")).hexdigest()
        if fingerprint in seen:
            stats["dropped:duplicate"] += 1
            continue
        seen.add(fingerprint)
        kept.append(example)
    stats["candidates"] = len(kept)
    stats["redactions_applied"] = sum(e["redactions"] for e in kept)
    stats["repo_checked_files"] = sum(e["checks"]["repo"]["checked"] for e in kept)
    return {"candidates": kept, "stats": stats}
