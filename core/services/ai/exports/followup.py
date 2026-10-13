"""A bare "export it to Excel" / "and as a PDF?" exports the previous answer instead of asking the model.

It is a follow-up only when a file is wanted AND the message names no data topic AND the query engine finds
no capability in it; "export the loans to excel" or "export my salaries 2026" are data questions and go
through the normal pipeline (their own answer then gets the links)."""

from __future__ import annotations

from typing import Any

from .document import strip_export_lines

FOLLOWUP_TOOL = "export_followup"


def is_pure_followup(routing: Any, understanding: Any) -> bool:
    """`routing`: query_engine Routing for the message; `understanding`: chat_pipeline Understanding."""
    return getattr(routing, "status", "") == "none" and not list(getattr(understanding, "topics", None) or [])


def previous_answer(conversation: Any, before_message_id: int) -> Any | None:
    """Latest earlier assistant answer that is real content (not an export-follow-up note)."""
    for msg in conversation.messages.filter(role="assistant", is_deleted=False, id__lt=before_message_id).order_by("-id"):
        calls = msg.tool_calls or []
        if any(isinstance(c, dict) and c.get("tool") == FOLLOWUP_TOOL for c in calls):
            continue
        if strip_export_lines(msg.content).strip():
            return msg
    return None
