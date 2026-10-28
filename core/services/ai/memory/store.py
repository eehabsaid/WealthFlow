"""Storage rules for the AI's own memory notes: per user, bounded, edited in place instead of duplicated."""

from __future__ import annotations

from typing import Any

from core.models import AIMemoryNote

MAX_NOTES = 80
TITLE_MAX = 120
BODY_MAX = 700


def _clean(text: Any, limit: int) -> str:
    return " ".join(str(text or "").split())[:limit]


def list_notes(user: Any) -> list[AIMemoryNote]:
    if user is None or not getattr(user, "is_authenticated", False):
        return []
    return list(AIMemoryNote.objects.filter(user=user))


def apply_edits(user: Any, data: dict, conversation_id: int | None = None) -> list[AIMemoryNote]:
    """Apply the model's edits {"notes": [{"id"?, "title", "body", "always"?}], "delete": [ids]}; returns the notes created or changed.
    An id that is not this user's note is ignored (a note is never created from a foreign id)."""
    changed: list[AIMemoryNote] = []
    if not isinstance(data, dict):
        return changed
    own = {n.id: n for n in list_notes(user)}
    for raw in data.get("delete") or []:
        note = own.pop(raw, None) if isinstance(raw, int) else None
        if note:
            note.delete()
    for item in data.get("notes") or []:
        if not isinstance(item, dict):
            continue
        title, body = _clean(item.get("title"), TITLE_MAX), _clean(item.get("body"), BODY_MAX)
        if not title or not body:
            continue
        note = own.get(item.get("id")) if isinstance(item.get("id"), int) else None
        if note is None:
            note = AIMemoryNote(user=user)
        note.title, note.body = title, body
        if isinstance(item.get("always"), bool):
            note.always = item["always"]
        note.source_conversation_id = conversation_id or note.source_conversation_id
        note.save()
        own[note.id] = note
        changed.append(note)
    overflow = sorted(own.values(), key=lambda n: (n.always, n.updated_at, n.id))[: max(0, len(own) - MAX_NOTES)]
    for note in overflow:   # oldest-updated notes go first (standing instructions last) when the model has not consolidated
        note.delete()
    return changed
