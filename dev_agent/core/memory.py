"""coding_agent/MEMORY.md: decisions and lessons that survive between sessions, one dated line each (same file and format the in-chat tools use)."""

from __future__ import annotations

import datetime

MAX_ENTRY = 400
SECRET_HINTS = ("password", "secret", "api_key", "apikey", "token", "bearer ")


class MemoryError_(ValueError):
    pass


def entries(project) -> list[str]:
    try:
        return [line[2:].strip() for line in (project.agent_dir / "MEMORY.md").read_text(encoding="utf-8").splitlines() if line.startswith("- ")]
    except OSError:
        return []


def add(project, text: str, today: datetime.date | None = None) -> str:
    clean = " ".join(str(text or "").split())[:MAX_ENTRY]
    if not clean:
        raise MemoryError_("empty entry")
    if any(h in clean.lower() for h in SECRET_HINTS):
        raise MemoryError_("this looks like it contains a secret; memory never stores secrets")
    if clean in [e.split(": ", 1)[-1] for e in entries(project)]:
        return "already recorded"
    line = f"- {(today or datetime.date.today()).isoformat()}: {clean}"
    with (project.agent_dir / "MEMORY.md").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
    return line
