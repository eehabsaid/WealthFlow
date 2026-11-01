"""Context picker: for a task, the skills, rules, past decisions and index entries that matter, cut to a character budget so a
local model's context never overflows. Keyword overlap only; no model."""

from __future__ import annotations

import re

from . import AGENT_DIR, index
from .memory import entries

WORD = re.compile(r"[a-z0-9_]{3,}")
STOP = {"the", "and", "for", "with", "that", "this", "from", "into", "add", "fix", "make", "use", "all", "new", "when", "not", "are", "should"}


def _words(text: str) -> set[str]:
    return {w for w in WORD.findall(text.lower()) if w not in STOP}


def _score(task: set[str], text: str, name: str = "") -> int:
    body = _words(text)
    return 3 * len(task & _words(name.replace("-", " ").replace("_", " "))) + len(task & body)


def pick(task: str, budget: int = 6000) -> dict:
    """{skills: [{name, text}], decisions: [...], index: [...], used_chars}. Skills/decisions first, then index hits."""
    words, left = _words(task), budget
    skills = []
    ranked = sorted(((_score(words, p.read_text(encoding="utf-8"), p.stem), p) for p in (AGENT_DIR / "skills").glob("*.md")), key=lambda t: -t[0])
    for score, p in ranked:
        text = p.read_text(encoding="utf-8")
        if score <= 0 or left < 400:
            break
        text = text[: min(len(text), max(400, left // 2))]
        skills.append({"name": p.stem, "text": text})
        left -= len(text)
    decisions = []
    for e in sorted(entries(), key=lambda e: -_score(words, e)):
        if _score(words, e) <= 0 or left < 150:
            break
        decisions.append(e[:300])
        left -= len(e[:300])
    hits = []
    for w in sorted(words, key=len, reverse=True)[:6]:
        for h in index.find(w, 6):
            line = f"{h['file']} ({h['lines']} lines) {', '.join(h['matches'][:4])}"
            if line not in hits and left > len(line):
                hits.append(line)
                left -= len(line)
    return {"skills": skills, "decisions": decisions, "index": hits[:25], "used_chars": budget - left}
