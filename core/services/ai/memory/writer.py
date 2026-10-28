"""After a chat turn, the model itself reads the recent exchange and its current notes, and decides what is worth
remembering: it edits an existing note when the topic is already there, adds a new one, or leaves memory alone.
No keyword rules and no fixed schema: the notes are free text written by the model."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from .store import BODY_MAX, apply_edits, list_notes

logger = logging.getLogger(__name__)

RECENT_MESSAGES = 6
_MSG_CHARS = 1200

_INSTRUCTIONS = (
    "You keep long-term memory notes for the user of a personal finance app, so they never have to repeat themselves in a new chat. "
    "Read the recent chat and your current notes. Keep what a helpful assistant would want to be reminded of later: the user's goals, "
    "results you reached together (with the numbers and their dates), decisions, and preferences. Skip small talk and anything "
    "that is only a live figure the app can look up again. Today is {today}; write dates into the note text. "
    "If a note already covers the topic, update it using its id (rewrite the whole note, do not duplicate). "
    "Delete a note only if the chat shows it is wrong or no longer true. Each note: a short title and a body under {body_max} characters. "
    "Answer with JSON only, no other text: {{\"notes\": [{{\"id\": <existing id or null>, \"title\": \"...\", \"body\": \"...\"}}], \"delete\": [<ids>]}}. "
    "If nothing is worth remembering, answer {{\"notes\": [], \"delete\": []}}."
)


def _extract_json(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _budget_chars(user: Any) -> int:
    from core.models import AppSettings

    try:
        return max(1000, int(AppSettings.get("ai_context_token_budget", "2048", user=user))) * 4
    except (TypeError, ValueError):
        return 2048 * 4


def build_messages(user: Any, conversation: Any) -> list[dict[str, str]] | None:
    recent = list(conversation.messages.filter(is_deleted=False, role__in=("user", "assistant")).order_by("-id")[:RECENT_MESSAGES])
    recent.reverse()
    if not recent or not any(m.role == "assistant" and (m.content or "").strip() for m in recent):
        return None
    budget = _budget_chars(user)
    chat, per = [], max(200, min(_MSG_CHARS, (budget // 2) // RECENT_MESSAGES))
    for m in recent:
        chat.append(f"{m.role.upper()}: {(m.content or '')[:per]}")
    notes_text, used = [], 0
    for n in list_notes(user):
        line = f"#{n.id} [{n.updated_at:%Y-%m-%d}] {n.title}: {n.body}"
        if used + len(line) > budget // 3:
            break
        notes_text.append(line)
        used += len(line)
    system = _INSTRUCTIONS.format(today=date.today().isoformat(), body_max=BODY_MAX)
    user_msg = "CURRENT NOTES:\n" + ("\n".join(notes_text) or "(none)") + "\n\nRECENT CHAT:\n" + "\n".join(chat)
    return [{"role": "system", "content": system}, {"role": "user", "content": user_msg}]


def update_memory(user: Any, conversation: Any, provider: Any) -> list:
    """Run one memory pass for this conversation. Returns the notes created or changed (empty list: nothing stored)."""
    messages = build_messages(user, conversation)
    if not messages or provider is None:
        return []
    # No small max_tokens here: with Settings > Reasoning = on the model thinks first, and a 500-token cap was spent entirely on the
    # thinking, leaving an empty answer. The UI-set max tokens apply instead; this runs in the background, so length costs the user nothing.
    res = provider.generate(messages, tools=None, temperature=0)
    if not isinstance(res, dict) or res.get("error"):
        logger.warning("memory writer: model call failed (%s), nothing stored", (res or {}).get("error") if isinstance(res, dict) else "no answer")
        return []
    answer = str(res.get("content") or "")
    data = _extract_json(answer)
    if data is None:
        logger.warning("memory writer: answer was not the expected JSON (%d chars: %r), nothing stored", len(answer), answer[:120])
        return []
    return apply_edits(user, data, conversation.id)
