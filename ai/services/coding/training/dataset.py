"""Point 9: a VERIFIED coding dataset from this repo's own history. An example is a past change that (a) touches source files and Django tests,
(b) touches no protected file, secret or database, (c) is small enough, and (d) whose own tests PASS when run on a clean checkout of that commit.
Nothing is kept on a guess: a change whose tests could not be run is dropped and counted."""

from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys
from collections import Counter
from typing import Callable

from ai.services.investigation import paths

from ai.services.coding.config import protected_reason
from ai.services.coding.training import history, settings


def is_test(path: str, cfg: dict) -> bool:
    """Each of `cfg["test_prefixes"]` is a directory prefix (an fnmatch pattern, so "ai/*/tests/" covers every "ai/<app>/tests/" folder without
    naming each one); any .py file under one of them counts as a test. A pattern with no wildcard behaves exactly like a plain prefix."""
    norm = path.replace("\\", "/")
    return norm.endswith(".py") and any(fnmatch.fnmatch(norm, p.rstrip("/") + "/*") for p in cfg["test_prefixes"])


def django_label(path: str) -> str:
    """ai/tests/test_x.py -> ai.tests.test_x (the top-level tests/ folder holds browser E2E modules, which are not Django tests)."""
    return path.removesuffix(".py").replace("/", ".") if not path.startswith("tests/") else ""


def held_out(sha: str, cfg: dict) -> bool:
    """Deterministic: the same commit is always held out, so the test set never leaks into training."""
    return int(sha[:8], 16) % max(2, int(cfg["held_out_every"])) == 0


def candidate(commit: dict, cfg: dict) -> tuple[dict | None, str]:
    """(example, "") for a usable change, else (None, why it was dropped)."""
    sha, parent = commit["sha"], commit["parent"]
    if not parent:
        return None, "no_parent"
    files = history.changed_files(sha)
    # only code files ever enter an example: the tracked database, .env and other data files in the same commit are simply left out
    src = [f for f in files if f.endswith(tuple(cfg["source_ext"])) and not is_test(f, cfg) and not paths.is_blocked_name(os.path.basename(f))]
    tests = [f for f in files if is_test(f, cfg)]
    labels = sorted({django_label(t) for t in tests} - {""})
    if not src:
        return None, "no_source_change"
    if not labels:
        return None, "no_django_test"
    if len(src) > cfg["max_source_files"]:
        return None, "too_many_files"
    if any(protected_reason(f) for f in src):
        return None, "protected_file"
    diff = history.diff_of(parent, sha, src)
    if not diff or len(diff) > cfg["max_diff_chars"]:
        return None, "diff_size"
    before = "\n\n".join(f"### {f}\n" + (history.file_at(parent, f) or "(new file)") for f in src)
    if len(before) > cfg["max_context_chars"]:
        return None, "context_too_long"
    task = (commit["subject"] + ("\n" + commit["body"] if commit["body"] else "")).strip()
    messages = [{"role": "system", "content": cfg["system_prompt"]},
                {"role": "user", "content": f"TASK: {task}\n\nFILES BEFORE THE CHANGE:\n{before}"},
                {"role": "assistant", "content": diff}]
    return {"sha": sha, "parent": parent, "subject": commit["subject"], "files": src, "tests": labels, "test_files": tests, "diff": diff, "messages": messages}, ""


def run_tests(sha: str, labels: list[str], timeout: int) -> bool:
    """True when the commit's own tests pass on a clean checkout of that commit."""
    try:
        with history.checkout(sha) as repo:
            done = subprocess.run([sys.executable, "manage.py", "test", *labels], cwd=repo, capture_output=True, timeout=timeout)
            return done.returncode == 0
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return False


def build(limit: int = 0, verify: bool = True, runner: Callable = run_tests, log: Callable[[str], None] = print) -> dict:
    """{"train": [...], "held_out": [...], "stats": Counter}. `verify=False` only counts candidates (nothing is trained on unverified changes)."""
    cfg, stats = settings(), Counter()
    out = {"train": [], "held_out": [], "stats": stats}
    for commit in history.commits(limit):
        stats["commits"] += 1
        example, why = candidate(commit, cfg)
        if example is None:
            stats["dropped:" + why] += 1
            continue
        stats["candidates"] += 1
        if not verify:
            continue
        log(f"Running the tests of {commit['sha'][:8]} ({commit['subject'][:60]}) ...")
        if not runner(commit["sha"], example["tests"], cfg["verify_timeout_s"]):
            stats["dropped:tests_do_not_pass"] += 1
            continue
        stats["verified"] += 1
        out["held_out" if held_out(commit["sha"], cfg) else "train"].append(example)
    return out


def write(result: dict, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    train = os.path.join(out_dir, "coding_train.jsonl")
    with open(train, "w", encoding="utf-8") as fh:
        for ex in result["train"]:
            fh.write(json.dumps({"messages": ex["messages"]}, ensure_ascii=False) + "\n")
    held = os.path.join(out_dir, "coding_heldout.json")
    with open(held, "w", encoding="utf-8") as fh:
        json.dump(result["held_out"], fh, ensure_ascii=False, indent=1)
    report = os.path.join(out_dir, "coding_dataset_report.txt")
    with open(report, "w", encoding="utf-8") as fh:
        fh.write("\n".join(f"{k}: {v}" for k, v in sorted(result["stats"].items())) + f"\ntraining examples: {len(result['train'])}\nheld-out examples: {len(result['held_out'])}\n")
    return {"train_file": train, "held_out_file": held, "report": report, "train": len(result["train"]), "held_out": len(result["held_out"])}
