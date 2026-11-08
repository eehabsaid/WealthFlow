"""Storage for the four memory files. Every write is atomic and locked; each file is capped (oldest entries drop first) so it never grows without limit."""

from __future__ import annotations

import datetime
import json

from ..core import fsutil

KINDS = ("architecture", "decisions", "lessons")
CAP = 150            # entries per file (keeps every file under 200 lines)
MAX_ENTRY = 400
SECRET_HINTS = ("password", "secret", "api_key", "apikey", "token", "bearer ", "passphrase")


class MemoryRefused(ValueError):
    pass


def folder(project):
    return project.agent_dir / "memory"


def _lock(project, name: str):
    return fsutil.file_lock(project.lock_dir, f"memory:{name}")


def clean(text) -> str:
    out = " ".join(str(text or "").split())[:MAX_ENTRY]
    if not out:
        raise MemoryRefused("empty entry")
    if any(h in out.lower() for h in SECRET_HINTS):
        raise MemoryRefused("this looks like it contains a secret; memory never stores secrets")
    return out


def _read(path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def entries(project, kind: str) -> list[str]:
    """Entries of architecture / decisions / lessons, oldest first, without the leading '- '."""
    return [line[2:].strip() for line in _read(folder(project) / f"{kind}.md") if line.startswith("- ")]


def add(project, kind: str, text, today: datetime.date | None = None) -> str:
    if kind not in KINDS:
        raise MemoryRefused(f"kind must be one of: {', '.join(KINDS)}")
    body = clean(text)
    with _lock(project, kind):
        rows = entries(project, kind)
        if body in [r.split(": ", 1)[-1] for r in rows]:
            return "already recorded"
        rows.append(f"{(today or datetime.date.today()).isoformat()}: {body}")
        fsutil.atomic_write(folder(project) / f"{kind}.md", ("\n".join(f"- {r}" for r in rows[-CAP:]) + "\n").encode("utf-8"))
    return rows[-1]


def forget(project, kind: str, needle: str) -> int:
    """Remove the entries of `kind` that contain `needle` (owner command). Returns how many were removed."""
    if kind not in KINDS or not needle.strip():
        raise MemoryRefused("give a kind and some text to look for")
    with _lock(project, kind):
        rows = entries(project, kind)
        keep = [r for r in rows if needle.lower() not in r.lower()]
        if len(keep) != len(rows):
            fsutil.atomic_write(folder(project) / f"{kind}.md", (("\n".join(f"- {r}" for r in keep) + "\n") if keep else "").encode("utf-8"))
    return len(rows) - len(keep)


def tasks(project) -> list[dict]:
    rows = []
    for line in _read(folder(project) / "tasks.jsonl"):
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue   # a damaged line is skipped, never fatal
    return rows


def record_task(project, row: dict) -> None:
    """One row per task id (a task that was stopped and later resumed is updated, not duplicated)."""
    with _lock(project, "tasks"):
        rows = [r for r in tasks(project) if r.get("id") != row["id"]] + [row]
        fsutil.atomic_write(folder(project) / "tasks.jsonl", ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows[-CAP:]) + "\n").encode("utf-8"))
