"""Memory block for the system prompt, sized from the UI-set token budget (never a fixed backend number):
standing instructions ("always" notes) in full, then a one-line-per-note index, then the notes that match the question."""

from __future__ import annotations

import re
from typing import Any

from .store import list_notes

_HOW = (
    "You remember across chats: when the user asks you to remember or save something call save_memory; to forget something call forget_memory (note ids "
    "below); save standing preferences (\"don't ask me again\") with always=true. Say briefly when you did."
)
HEADER = (
    "\n\nLONG-TERM MEMORY: " + _HOW + " Notes are dated reminders and can be out of date; live data wins. read_memory opens a note."
)
EMPTY_HINT = "\n\nLONG-TERM MEMORY: " + _HOW + " No notes are saved yet. Never say you cannot remember across chats."
STANDING = "\nSTANDING INSTRUCTIONS FROM THE USER (always follow them):"
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
    """Standing instructions in full (at most half of the budget), the dated index of all notes, and the best-matching notes, within token_limit."""
    notes = list_notes(user)
    if not notes:
        return EMPTY_HINT
    budget = token_limit * 4
    block, used = HEADER, len(HEADER)
    standing = [n for n in notes if n.always]
    if standing:
        block += STANDING
        used += len(STANDING)
        for note in standing:
            line = f"\n- {note.title}: {note.body}"
            if used + len(line) > budget // 2 + len(HEADER):
                break
            block += line
            used += len(line)
    lines = []
    for note in notes:
        line = _line(note)
        if used + len(line) + 1 > budget - _MORE_ROOM:   # keep room for the "older notes" line so the block never exceeds the budget
            lines.append(f"- (+{len(notes) - len(lines)} older notes: call read_memory with a query to find them)")
            break
        lines.append(line)
        used += len(line) + 1
    block += "\nNOTES INDEX:\n" + "\n".join(lines)
    for note in relevant_notes([n for n in notes if not n.always], query):
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
