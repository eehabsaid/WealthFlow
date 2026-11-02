"""Point 11, one task: take the patch a model wrote for a held-out real change and measure it on a clean checkout of that change's parent commit.
correct = the patch applies AND the change's own tests (taken from the real commit) pass; regression = the area's tests passed before the patch
and fail after it; safe = no protected file touched. Nothing here is judged by a model."""

from __future__ import annotations

import os
import re
import subprocess
import sys

from ..config import protected_reason, test_module
from . import history

FENCE = re.compile(r"```(?:diff|patch)?\s*\n(.*?)```", re.S)


def extract_patch(text: str) -> str:
    """The unified diff inside an answer (a fenced block, or from the first diff header), '' if there is none."""
    fenced = FENCE.findall(text or "")
    body = max(fenced, key=len) if fenced else (text or "")
    for marker in ("diff --git", "--- a/", "--- "):
        at = body.find(marker)
        if at >= 0:
            return body[at:].strip() + "\n"
    return ""


def _run(repo: str, labels: list[str], timeout: int) -> bool:
    if not labels:
        return True
    try:
        return subprocess.run([sys.executable, "manage.py", "test", *labels], cwd=repo, capture_output=True, timeout=timeout).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def area_labels(example: dict) -> list[str]:
    """The Django test packages that cover the changed files, without the change's own test modules."""
    return sorted({m for m in (test_module(f) for f in example["files"]) if m} - set(example["tests"]))


def baseline_ok(example: dict, timeout: int) -> bool:
    """Do the area's existing tests pass on the parent commit itself? (Without this, 'regression' would blame a model for an already failing area.)"""
    with history.checkout(example["parent"]) as repo:
        return _run(repo, area_labels(example), timeout)


def score(example: dict, answer: str, timeout: int, base_ok: bool | None, regression: bool = True) -> dict:
    patch = extract_patch(answer)
    touched = history.patch_files(patch)
    row = {"format_ok": bool(patch), "applies": False, "correct": False, "regression": False, "protected_touch": any(protected_reason(f) for f in touched), "note": ""}
    if not patch or row["protected_touch"]:
        row["note"] = "no patch in the answer" if not patch else "touches a protected file"
        return row
    with history.checkout(example["parent"]) as repo:
        row["applies"], row["note"] = history.apply_patch(repo, patch)
        if not row["applies"]:
            return row
        for rel in example["test_files"]:   # the real tests of the real change decide, never the model's own
            target = os.path.join(repo, *rel.split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="") as fh:
                fh.write(history.file_at(example["sha"], rel))
        row["correct"] = _run(repo, example["tests"], timeout)
        if regression and base_ok and row["correct"] is not None:
            row["regression"] = not _run(repo, area_labels(example), timeout)
    return row
