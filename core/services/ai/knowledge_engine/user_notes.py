"""
Per-user learned notes for AIKnowledgeEngine.

Learns automatically from every chat turn, for ALL modules, without storing any
financial values (those are always read live from the tools, so they can never
go stale). Two kinds of notes are kept, in the user's own words:
  - teach:      "remember that...", "from now on...", "when I say X I mean Y"
  - correction: the user says the previous data-based answer was wrong
Notes live in AppSettings under the user (owner=user), so they are never shared
with other customers, unlike the global AIKnowledgeEntry table.
"""

from __future__ import annotations

import json
from typing import Any

NOTES_KEY = "ai_learned_notes"
MAX_NOTES = 20
MAX_NOTES_IN_PROMPT = 10

_TEACH_CUES = (
    "remember that", "remember:", "from now on", "always answer", "always show",
    "never show", "when i say", "note that", "keep in mind",
    "تذكر", "من الآن", "عندما أقول", "دائما اعرض", "دائماً اعرض",
)
_CORRECTION_CUES = (
    "wrong", "incorrect", "not correct", "not right", "that's not", "thats not",
    "i meant", "you mixed", "mistake",
    "غلط", "خطأ", "خاطئ", "مش صح", "ليس صحيح", "قصدت", "أقصد",
)


def _clip(text: str, limit: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class UserNotesMixin:
    @classmethod
    def load_user_notes(cls, user: Any) -> list[str]:
        from core.models import AppSettings

        if user is None or not getattr(user, "is_authenticated", False):
            return []
        try:
            data = json.loads(AppSettings.get(NOTES_KEY, "[]", user=user) or "[]")
        except (ValueError, TypeError):
            return []
        return [str(n) for n in data if str(n).strip()] if isinstance(data, list) else []

    @classmethod
    def _save_user_note(cls, user: Any, note: str) -> None:
        from core.models import AppSettings

        notes = [n for n in cls.load_user_notes(user) if n != note]
        notes.append(note)
        AppSettings.set(NOTES_KEY, json.dumps(notes[-MAX_NOTES:], ensure_ascii=False), user=user)

    @classmethod
    def record_user_notes_from_turn(
        cls, user: Any, user_text: str, previous_question: str = "", previous_used_tools: bool = False
    ) -> str | None:
        """Learn one note from this turn (if any). Returns the saved note or None."""
        if user is None or not getattr(user, "is_authenticated", False):
            return None
        low = (user_text or "").lower()
        if any(cue in low for cue in _TEACH_CUES):
            note = f"[teach] {_clip(user_text, 220)}"
        elif previous_used_tools and previous_question and any(cue in low for cue in _CORRECTION_CUES):
            note = (
                f"[correction] For the question \"{_clip(previous_question, 100)}\" "
                f"the user said the answer was wrong: \"{_clip(user_text, 160)}\". "
                "Re-check the exact field and period in the tool data before answering similar questions."
            )
        else:
            return None
        cls._save_user_note(user, note)
        return note

    @classmethod
    def build_user_notes_context(cls, user: Any) -> str:
        notes = cls.load_user_notes(user)[-MAX_NOTES_IN_PROMPT:]
        if not notes:
            return ""
        lines = ["\n\nLEARNED NOTES FROM THIS USER'S PAST CHATS (live tool data always overrides these notes):"]
        lines += [f"- {n}" for n in notes]
        return "\n".join(lines)
