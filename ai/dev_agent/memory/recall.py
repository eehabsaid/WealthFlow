"""Pick the memory that matters for a task (keyword overlap, recent first) and cut it to a character budget, so it never bloats the context."""

from __future__ import annotations

import re

from ai.dev_agent.memory import store

WORD = re.compile(r"[a-z0-9_]{3,}")
STOP = {"the", "and", "for", "with", "that", "this", "from", "into", "add", "fix", "make", "use", "all", "new", "when", "not", "are", "should"}
TITLES = {"architecture": "Architecture notes", "decisions": "Decisions", "lessons": "Lessons", "rules": "Confirmed business rules", "tasks": "Earlier tasks"}


def _words(text: str) -> set[str]:
    return {w for w in WORD.findall(text.lower()) if w not in STOP}


def _task_line(row: dict) -> str:
    files = ", ".join(row.get("files", [])[:4])
    return f"{row.get('date', '')} {row.get('id', '')} [{row.get('status', '')}] {row.get('goal', '')}" + (f" (files: {files})" if files else "") + (f" - {row['reason']}" if row.get("reason") else "")


def pick(project, task: str, budget: int = 2000) -> dict:
    """{architecture: [...], decisions: [...], lessons: [...], tasks: [...]}: only entries that share words with the task, best and newest first."""
    words, out, left = _words(task), {}, budget
    sources = {k: store.entries(project, k) for k in store.KINDS}
    sources["tasks"] = [_task_line(r) for r in store.tasks(project)]
    for kind, rows in sources.items():
        ranked = sorted(((len(words & _words(r)), i, r) for i, r in enumerate(rows)), key=lambda t: (-t[0], -t[1]))
        chosen = []
        for score, _, row in ranked:
            if score <= 0 or left < 120 or len(chosen) >= 5:
                break
            chosen.append(row[:260])
            left -= len(chosen[-1])
        if chosen:
            out[kind] = chosen
    return out


def render(picked: dict) -> str:
    return "\n\n".join(f"## Memory - {TITLES[k]}\n" + "\n".join(f"- {r}" for r in rows) for k, rows in picked.items())
