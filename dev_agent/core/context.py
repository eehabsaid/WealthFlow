"""Context picker: for a task, the skills, past decisions and index entries that matter, cut to a character budget. Keyword overlap only.
Adapted from core/services/ai/coding/context.py; reads <project>/coding_agent/skills and MEMORY.md."""

from __future__ import annotations

import re

from . import memory

WORD = re.compile(r"[a-z0-9_]{3,}")
STOP = {"the", "and", "for", "with", "that", "this", "from", "into", "add", "fix", "make", "use", "all", "new", "when", "not", "are", "should"}


def _words(text: str) -> set[str]:
    return {w for w in WORD.findall(text.lower()) if w not in STOP}


def _score(task: set[str], text: str, name: str = "") -> int:
    return 3 * len(task & _words(name.replace("-", " ").replace("_", " "))) + len(task & _words(text))


def pick(project, index, task: str, budget: int = 6000) -> dict:
    """{skills: [{name, text}], decisions: [...], files: [...], used_chars}; skills and decisions first, then index hits."""
    words, left = _words(task), budget
    skills = []
    folder = project.agent_dir / "skills"
    docs = sorted(folder.glob("*.md")) if folder.is_dir() else []
    ranked = sorted(((_score(words, p.read_text(encoding="utf-8", errors="replace"), p.stem), p) for p in docs), key=lambda t: -t[0])
    for score, path in ranked:
        if score <= 0 or left < 400:
            break
        text = path.read_text(encoding="utf-8", errors="replace")
        text = text[: min(len(text), max(400, left // 2))]
        skills.append({"name": path.stem, "text": text})
        left -= len(text)
    decisions = []
    for entry in sorted(memory.entries(project), key=lambda e: -_score(words, e)):
        if _score(words, entry) <= 0 or left < 150:
            break
        decisions.append(entry[:300])
        left -= len(decisions[-1])
    files = []
    for row in index.search(task, 12):
        if left < 120:
            break
        files.append(row)
        left -= 120
    return {"skills": skills, "decisions": decisions, "files": files, "used_chars": budget - left}


def render(picked: dict) -> str:
    parts = [f"## Skill: {s['name']}\n{s['text']}" for s in picked["skills"]]
    if picked["decisions"]:
        parts.append("## Past decisions\n" + "\n".join(f"- {d}" for d in picked["decisions"]))
    if picked["files"]:
        parts.append("## Likely files\n" + "\n".join(f"- {f['path']} ({f['lines']} lines)" for f in picked["files"]))
    return "\n\n".join(parts)
