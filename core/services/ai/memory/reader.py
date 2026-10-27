"""The read_memory tool: lets the model open the notes it decides are relevant."""

from __future__ import annotations

from typing import Any

from .index import relevant_notes
from .store import list_notes

NAME = "read_memory"
_DESC = ("Open notes from your long-term memory (reminders you wrote after earlier chats). Pass `ids` from the memory index, "
         "or a `query` to find notes by topic. Notes are dated reminders, not live facts: re-check live data when accuracy matters.")


def read_memory(user: Any, params: dict) -> dict:
    notes = list_notes(user)
    ids = [i for i in (params.get("ids") or []) if isinstance(i, int)]
    picked = [n for n in notes if n.id in ids] if ids else relevant_notes(notes, str(params.get("query") or ""), limit=5)
    return {"notes": [{"id": n.id, "title": n.title, "date": f"{n.updated_at:%Y-%m-%d}", "text": n.body} for n in picked],
            "note": "These are reminders from earlier chats, not live data; re-check the live data when accuracy matters."}


TOOL_DEF = {
    "name": NAME, "description": _DESC, "is_read_only": True, "tier": "read", "domain": "memory", "offer_all_domains": True,
    "handler": lambda user, params: read_memory(user, params),
    "schema": {"type": "function", "function": {"name": NAME, "description": _DESC, "parameters": {"type": "object", "properties": {
        "ids": {"type": "array", "items": {"type": "integer"}, "description": "note numbers from the memory index"},
        "query": {"type": "string", "description": "topic words, used when you have no ids"},
    }}}},
}
