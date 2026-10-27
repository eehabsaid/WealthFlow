"""Compact memory index for the system prompt, sized from the UI-set token budget (never a fixed backend number)."""

from __future__ import annotations

import re
from typing import Any

from .store import list_notes

HEADER = (
    "\n\nLONG-TERM MEMORY (reminders you wrote after earlier chats, each dated; they can be out of date, so when "
    "accuracy matters re-check live data, which always wins. Open a note with the read_memory tool when it is relevant):"
)
_WORD = re.compile(r"\w{3,}", re.UNICODE)
_MORE_ROOM = 100


def _line(note: Any) -> str:
    return f"- #{note.id} [{note.updated_at:%Y-%m-%d}] {note.title}"


def _words(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text or "")}


def relevant_notes(notes: list, query: str, limit: int = 2) -> list:
    """Notes sharing the most words with the question: pre-loaded for models that are weak at calling tools."""
    q = _words(query)
    scored = [(len(q & _words(f"{n.title} {n.body}")), n) for n in notes]
    return [n for score, n in sorted(scored, key=lambda s: -s[0])[:limit] if score >= 2]


def build_memory_block(user: Any, query: str = "", token_limit: int = 300) -> str:
    """Index (one line per note, newest first) plus the full text of the best-matching notes, within token_limit."""
    notes = list_notes(user)
    if not notes:
        return ""
    budget = token_limit * 4
    lines, used = [], len(HEADER)
    for note in notes:
        line = _line(note)
        if used + len(line) + 1 > budget - _MORE_ROOM:   # keep room for the "older notes" line so the block never exceeds the budget
            lines.append(f"- (+{len(notes) - len(lines)} older notes: call read_memory with a query to find them)")
            break
        lines.append(line)
        used += len(line) + 1
    block = HEADER + "\n" + "\n".join(lines)
    for note in relevant_notes(notes, query):
        extra = f"\n  #{note.id} details: {note.body}"
        if used + len(extra) > budget * 2:
            break
        block += extra
        used += len(extra)
    return block


def ui_token_limit(user: Any) -> int:
    """A fifth of the user's UI-set context token budget (the code defaults only apply when nothing is set)."""
    from core.models import AppSettings

    try:
        return max(150, int(AppSettings.get("ai_context_token_budget", "2048", user=user)) // 5)
    except (TypeError, ValueError):
        return 409


def build_memory_block_for_ui(user: Any, query: str = "") -> str:
    return build_memory_block(user, query, token_limit=ui_token_limit(user))
