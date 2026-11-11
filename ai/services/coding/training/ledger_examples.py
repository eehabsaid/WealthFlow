"""Ledger-based training examples: completed, VERIFIED tasks from the standalone coding agent's own history (coding_agent/tasks/*/ledger.json)
become training examples, in two independent kinds:

  qa    - a read-only investigation/QA task (status "answered"): the goal and the agent's final answer.
  patch - an implementation task (status "completed", final verification VERIFIED): the goal, the files' content before the task, and the
          task's own frozen result diff (ledger.freeze_result_diffs(), point 3 of the training project).

Only tasks the agent itself marked finished and verified ever become a candidate; a failed, stopped, rejected or unverified task is skipped.
The ledger stores little on purpose (final answer, files, verification) - nothing here invents data the agent did not actually record."""

from __future__ import annotations

import hashlib
import os
import re
from collections import Counter
from difflib import SequenceMatcher

from ai.dev_agent.core.project import Project
from ai.dev_agent.engine import verify
from ai.dev_agent.ledger.ledger import Ledger
from ai.services.coding import ROOT
from ai.services.coding.config import protected_reason
from ai.services.coding.training import settings
from ai.services.coding.training.dataset import is_test
from ai.services.investigation import paths

KINDS = ("qa", "patch")

# Beyond paths.redact's secret/token masking: emails, phone numbers and currency-looking amounts, so a stray personal/financial detail an
# investigation answer happened to quote never reaches a training file. Over-redaction here is the safe failure mode.
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\-\s()]{7,}\d)(?!\w)")
_MONEY = re.compile(r"(?<![\w.])(?:[$£€]\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?(?:USD|EGP|EUR|GBP|SAR|AED))(?![\w.])", re.I)


def project() -> Project:
    return Project(ROOT)


def config(kind: str) -> dict:
    assert kind in KINDS, f"unknown example kind: {kind}"
    return settings(f"{kind}_training.json")


def redact_pii(text: str, cfg: dict) -> tuple[str, int]:
    """(text with secrets/tokens/PII masked, how many PII spots were masked). Secrets/tokens are always masked; emails/phones/amounts only
    when `redact_patterns` is on in the type's config, so a project can turn that extra pass off if its own data makes it too aggressive."""
    text = paths.redact(text)
    if not cfg.get("redact_patterns", True):
        return text, 0
    hits = 0

    def _mask(pattern):
        nonlocal hits, text
        text, n = pattern.subn("***REDACTED***", text)
        hits += n

    _mask(_EMAIL)
    _mask(_PHONE)
    _mask(_MONEY)
    return text, hits


def _fingerprint(text: str) -> str:
    return hashlib.sha1(" ".join(text.split()).lower().encode("utf-8")).hexdigest()


def held_out(key: str, cfg: dict) -> bool:
    """Deterministic: the same task is always held out, so the test set never leaks into training (same scheme as the git-history dataset,
    keyed by the task id instead of a commit sha)."""
    return int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:8], 16) % max(2, int(cfg["held_out_every"])) == 0


def validate_structure(example: dict, cfg: dict) -> str:
    """'' when `example` is well-formed and within the size limits, else why it was dropped."""
    if not example.get("messages") or len(example["messages"]) < 3:
        return "malformed_example"
    user, assistant = example["messages"][1]["content"], example["messages"][2]["content"]
    if not user.strip() or not assistant.strip():
        return "empty_content"
    if len(user) > cfg["max_context_chars"]:
        return "context_too_long"
    limit = cfg.get("max_answer_chars") or cfg.get("max_diff_chars")
    if limit and len(assistant) > limit:
        return "answer_too_long"
    return ""


def qa_candidate(ledger_data: dict, cfg: dict) -> tuple[dict | None, str]:
    d = ledger_data
    if d.get("status") != "answered":
        return None, "not_answered"
    goal, answer = str(d.get("goal") or "").strip(), str(d.get("answer") or "").strip()
    if not goal or not answer:
        return None, "empty_goal_or_answer"
    goal, g_hits = redact_pii(goal, cfg)
    answer, a_hits = redact_pii(answer, cfg)
    messages = [{"role": "system", "content": cfg["system_prompt"]}, {"role": "user", "content": f"QUESTION: {goal}"}, {"role": "assistant", "content": answer}]
    example = {"task_id": d["id"], "kind": "qa", "goal": goal, "answer": answer, "messages": messages, "redactions": g_hits + a_hits}
    why = validate_structure(example, cfg)
    return (None, why) if why else (example, "")


def patch_candidate(ledger: Ledger, cfg: dict) -> tuple[dict | None, str]:
    d = ledger.data
    if d.get("status") != "completed":
        return None, "not_completed"
    final = next((v for v in reversed(d["verification"]) if v["label"] == "final"), None)
    if not final or verify.overall(final["results"]) != "VERIFIED":
        return None, "not_verified"
    diffs = d.get("result_diffs") or {}
    src = sorted(f for f in ledger.changed_files() if not is_test(f, cfg) and not paths.is_blocked_name(os.path.basename(f)) and f in diffs)
    if not src:
        return None, "no_source_diff"   # only test files changed, or the task predates result_diffs (point 3, built going forward)
    if len(src) > cfg["max_source_files"]:
        return None, "too_many_files"
    if any(protected_reason(f) for f in src):
        return None, "protected_file"
    diff = "\n".join(diffs[f] for f in src)
    diff, d_hits = redact_pii(diff, cfg)
    if len(diff) > cfg["max_diff_chars"]:
        return None, "diff_size"
    before_parts, b_hits = [], 0
    for f in src:
        known, content = ledger.original(f)
        text = (content.decode("utf-8", "replace") if content is not None else "(new file)") if known else "(unknown before state)"
        text, hits = redact_pii(text, cfg)
        b_hits += hits
        before_parts.append(f"### {f}\n{text}")
    before = "\n\n".join(before_parts)
    if len(before) > cfg["max_context_chars"]:
        return None, "context_too_long"
    goal, g_hits = redact_pii(str(d.get("goal") or "").strip(), cfg)
    if not goal:
        return None, "empty_goal"
    messages = [{"role": "system", "content": cfg["system_prompt"]}, {"role": "user", "content": f"TASK: {goal}\n\nFILES BEFORE THE CHANGE:\n{before}"},
                {"role": "assistant", "content": diff}]
    example = {"task_id": d["id"], "kind": "patch", "goal": goal, "files": src, "diff": diff, "messages": messages, "redactions": d_hits + b_hits + g_hits}
    why = validate_structure(example, cfg)
    return (None, why) if why else (example, "")


def _dedup(examples: list[dict], cfg: dict, stats: Counter) -> list[dict]:
    """Exact duplicates (same normalized goal+answer/diff) are dropped outright; near-duplicates (ratio >= dedup_similarity) keep only the
    first one seen, oldest task id first, so reruns stay deterministic."""
    seen_exact, kept = set(), []
    for ex in sorted(examples, key=lambda e: e["task_id"]):
        fp = _fingerprint(ex["goal"] + "\n" + ex["messages"][2]["content"])
        if fp in seen_exact:
            stats["dropped:duplicate_exact"] += 1
            continue
        threshold = cfg.get("dedup_similarity", 0.92)
        near = next((k for k in kept if SequenceMatcher(None, ex["messages"][2]["content"], k["messages"][2]["content"]).ratio() >= threshold), None)
        if near is not None:
            stats["dropped:duplicate_near"] += 1
            continue
        seen_exact.add(fp)
        kept.append(ex)
    return kept


def extract(kind: str, project_: Project | None = None) -> dict:
    """{"candidates": [...], "stats": Counter}. Every completed/verified task is looked at; nothing is split or written here - that happens
    once the owner has approved candidates (see ledger_review.py)."""
    cfg = config(kind)
    proj = project_ or project()
    stats = Counter()
    candidates: list[dict] = []
    for task_id in Ledger.list_ids(proj):
        stats["tasks"] += 1
        try:
            ledger = Ledger.load(proj, task_id)
        except FileNotFoundError:
            stats["dropped:unreadable"] += 1
            continue
        example, why = (qa_candidate(ledger.data, cfg) if kind == "qa" else patch_candidate(ledger, cfg))
        if example is None:
            stats["dropped:" + why] += 1
            continue
        candidates.append(example)
    before = len(candidates)
    candidates = _dedup(candidates, cfg, stats)
    stats["candidates_before_dedup"] = before
    stats["candidates"] = len(candidates)
    stats["redactions_applied"] = sum(ex["redactions"] for ex in candidates)
    return {"candidates": candidates, "stats": stats}
