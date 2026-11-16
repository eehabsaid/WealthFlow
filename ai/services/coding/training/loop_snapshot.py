"""The throw-away working copy the real-loop evaluation runs in, so a run can never touch your repo, your task history or your Settings.

snapshot()   one copy of the working tree as it is on disk NOW (tracked files plus untracked files git does not ignore, so uncommitted dev-agent work is in it),
             made as a shared git clone (the agent's read-only `git` tool then works exactly as in your repo) overlaid with the files on disk. Your task history
             and the agent's memory notes are left out: a run must not see earlier runs, nor the answers of the very tasks it is being tested on.
fresh_copy() a private copy of the snapshot for ONE task of ONE model, so no run can influence another.
pin_model()  points that copy's coding_agent/agent_settings.json at the model under test (provider ollama); every other value stays as in your settings."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

SKIP = ("coding_agent/tasks", "coding_agent/memory", "coding_agent/.locks")


def _skipped(rel: str) -> bool:
    return any(rel == prefix or rel.startswith(prefix + "/") for prefix in SKIP)


def _git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True).stdout


def _writable(func, path, _exc) -> None:   # rmtree on Windows refuses read-only files (git objects)
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove(path) -> None:
    if Path(path).exists():
        shutil.rmtree(path, onerror=_writable)


def _plain_copy(root: Path, dest: Path) -> int:
    def ignore(folder, names):
        rel = os.path.relpath(folder, root).replace("\\", "/")
        return [n for n in names if n in (".git", "__pycache__") or _skipped(f"{rel}/{n}".removeprefix("./"))]

    shutil.copytree(root, dest, ignore=ignore)
    return sum(len(files) for _, _, files in os.walk(dest))


def snapshot(root, dest) -> dict:
    """Copy the working tree of `root` into `dest` (replacing it). Returns {"files", "git"}: how many files, and whether the copy has a git history."""
    root, dest = Path(root).resolve(), Path(dest)
    remove(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not (root / ".git").exists():
        return {"files": _plain_copy(root, dest), "git": False}
    subprocess.run(["git", "clone", "--quiet", "--shared", str(root), str(dest)], capture_output=True, check=True)
    names = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").decode("utf-8", "replace").split("\0")
    listed = sorted({n for n in names if n and not _skipped(n)})
    copied = 0
    for rel in listed:
        source, target = root / rel, dest / rel
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
        elif not source.exists():   # tracked, but deleted on disk: the copy must not bring it back
            target.unlink(missing_ok=True)
    for prefix in SKIP:
        remove(dest / prefix)
    return {"files": copied, "git": True}


def fresh_copy(source, dest) -> Path:
    dest = Path(dest)
    remove(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest, symlinks=True)
    return dest


def pin_model(root, model: str) -> dict:
    """Make the agent in `root` use `model` through Ollama. Returns the settings written."""
    path = Path(root) / "coding_agent" / "agent_settings.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data["provider"], data["model"] = "ollama", model
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data
