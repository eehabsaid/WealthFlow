"""Project rules for the system prompt, AGENTS.md style: the files named in `rules_files` of coding_agent/config.json (default AGENTS.md at the project root and
coding_agent/AGENTS.md), read fresh for every conversation, cut to a size that cannot crowd out the work. Pure reading; never written by the agent."""

from __future__ import annotations

DEFAULT_FILES = ["AGENTS.md", "coding_agent/AGENTS.md"]
PER_FILE = 6000
TOTAL = 9000


def load(project) -> str:
    files = project.config.get("rules_files") or DEFAULT_FILES
    parts, left = [], TOTAL
    for name in files:
        try:
            rel, full = project.resolve(name)
            if project.secret_reason(rel) or not full.is_file():
                continue
            text = full.read_text(encoding="utf-8", errors="replace").strip()
        except (OSError, ValueError):   # PathError is a ValueError: a bad name in the config is skipped, not fatal
            continue
        if not text or left < 200:
            continue
        text = text[: min(PER_FILE, left)] + ("\n[...rest of the file omitted: read it with read_file]" if len(text) > min(PER_FILE, left) else "")
        parts.append(f"### {rel}\n{text}")
        left -= len(text)
    return ("## Project rules (the owner's instructions; they outrank your own habits)\n" + "\n\n".join(parts)) if parts else ""
