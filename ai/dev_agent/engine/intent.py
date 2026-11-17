"""Is a task a request to CHANGE files, or only a question? Decided from the owner's own words (no model involved), so a model that says "done" without
planning or editing cannot turn a change request into an answer. A task that says "Answer only; do not plan or change anything." or asks a question stays read-only."""

from __future__ import annotations

import re

READ_ONLY = re.compile(r"answer only|do not plan|don't plan|read[- ]only", re.I)
QUESTION = re.compile(r"^\s*(?:what|where|which|who|why|how|when|does|do|is|are|can|explain|describe|summari[sz]e|list|show|tell|find)\b", re.I)
CHANGE = re.compile(r"(?:^|[.:;!]\s+)(?:please\s+)?(?:add|write|fix|rename|remove|delete|create|implement|refactor|update|change|replace|move|convert|rewrite|extract|insert|make|annotate|document)\b", re.I)


def needs_changes(task: str) -> bool:
    text = (task or "").strip()
    if READ_ONLY.search(text) or QUESTION.match(text):
        return False
    return bool(CHANGE.search(text))


def wrote_files(ledger) -> bool:
    """True when this task really changed a file on disk (written, deleted or left half-rolled-back)."""
    return any(f["state"] in ("written", "deleted", "rollback_failed") for f in ledger.data["files"].values())


NO_PLAN = ("You answered with {\"final\"} but the TASK asks you to change files, and no change was made. A change task is never finished by words: reply with a {\"plan\": ...} "
           "naming the file to edit. Do not say it is done.")
