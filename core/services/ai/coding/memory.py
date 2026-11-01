"""coding_agent/MEMORY.md: decisions and lessons that must survive between sessions, one dated line each. Append-only from the scripts."""

from __future__ import annotations

import datetime

from . import AGENT_DIR

FILE = AGENT_DIR / "MEMORY.md"
MAX_ENTRY = 400
SECRET_HINTS = ("password", "secret", "api_key", "apikey", "token", "bearer ")


class MemoryError_(ValueError):
    pass


def entries() -> list[str]:
    try:
        return [l[2:].strip() for l in FILE.read_text(encoding="utf-8").splitlines() if l.startswith("- ")]
    except OSError:
        return []


def add(text: str, today: datetime.date | None = None) -> str:
    clean = " ".join(str(text or "").split())[:MAX_ENTRY]
    if not clean:
        raise MemoryError_("empty entry")
    if any(h in clean.lower() for h in SECRET_HINTS):
        raise MemoryError_("this looks like it contains a secret; memory never stores secrets")
    line = f"- {(today or datetime.date.today()).isoformat()}: {clean}"
    if line.split(": ", 1)[1] in [e.split(": ", 1)[-1] for e in entries()]:
        return "already recorded"
    with FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return line
