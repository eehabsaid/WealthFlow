"""Tools that let the chat model itself obey the user's memory commands during the chat, the way Claude does:
"remember / save this" -> save_memory, "forget that" -> forget_memory, "from now on / don't ask me again" -> save_memory(always=true).
They change only the user's own memory notes (never business data), so they are allowed in read-only mode."""

from __future__ import annotations

from typing import Any

from .reader import TOOL_DEF as READ_TOOL_DEF
from .store import apply_edits, list_notes

_S = {"type": "string"}


def save_memory(user: Any, params: dict) -> dict:
    note_id = params.get("id")
    saved = apply_edits(user, {"notes": [{"id": note_id if isinstance(note_id, int) else None, "title": params.get("title"),
                                          "body": params.get("body"), "always": bool(params.get("always"))}]})
    if not saved:
        return {"error": "give a short `title` and the `body` text of the note"}
    note = saved[0]
    return {"ok": True, "id": note.id, "saved": f"#{note.id} {note.title}", "always": note.always,
            "note": "Saved. Tell the user briefly that you saved it to your memory."}


def forget_memory(user: Any, params: dict) -> dict:
    ids = [i for i in (params.get("ids") or []) if isinstance(i, int)]
    own = {n.id: n for n in list_notes(user)}
    gone = [own[i].title for i in ids if i in own]
    apply_edits(user, {"delete": [i for i in ids if i in own]})
    if not gone:
        return {"error": "none of those ids is one of your notes; look at the memory index (or call read_memory with a query) to find the right id"}
    return {"ok": True, "forgotten": gone, "note": "Deleted. Tell the user briefly that you forgot it."}


_SAVE_DESC = ("Save something to your long-term memory (a note that survives into every later chat). Use it when the user asks you to remember, save "
              "or note something, and for their standing instructions and preferences (e.g. 'don't ask me again about X', 'always answer in EGP'): "
              "set always=true for those so they apply in every chat. To change an existing note pass its id instead of making a duplicate. "
              "Write dates and numbers into the body.")
_FORGET_DESC = ("Delete notes from your long-term memory when the user asks you to forget, remove or ignore something. Pass the note ids from the memory "
                "index (use read_memory with a query if you are not sure which note it is).")

SAVE_TOOL_DEF = {
    "name": "save_memory", "description": _SAVE_DESC, "is_read_only": True, "tier": "read", "domain": "memory", "offer_all_domains": True,
    "handler": lambda user, params: save_memory(user, params),
    "schema": {"type": "function", "function": {"name": "save_memory", "description": _SAVE_DESC, "parameters": {"type": "object", "properties": {
        "title": {**_S, "description": "short title of the note"},
        "body": {**_S, "description": "the note text, with dates and numbers"},
        "id": {"type": "integer", "description": "id of an existing note to update instead of adding a new one"},
        "always": {"type": "boolean", "description": "true for a standing instruction or preference that must apply in every chat"},
    }, "required": ["title", "body"]}}},
}
FORGET_TOOL_DEF = {
    "name": "forget_memory", "description": _FORGET_DESC, "is_read_only": True, "tier": "read", "domain": "memory", "offer_all_domains": True,
    "handler": lambda user, params: forget_memory(user, params),
    "schema": {"type": "function", "function": {"name": "forget_memory", "description": _FORGET_DESC, "parameters": {"type": "object", "properties": {
        "ids": {"type": "array", "items": {"type": "integer"}, "description": "note ids to delete"},
    }, "required": ["ids"]}}},
}

MEMORY_TOOL_DEFS = {d["name"]: d for d in (READ_TOOL_DEF, SAVE_TOOL_DEF, FORGET_TOOL_DEF)}
