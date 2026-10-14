"""A bare "export it to Excel" / "and as a PDF?" exports the previous answer instead of asking the model.

It is a follow-up only when a file is wanted AND there is an earlier answer to export AND the message names no data
topic AND the query engine finds no capability in it AND little else is left once the file request is removed
("export it to pdf" leaves two words; "analyze my wealth ... in details and export to word" leaves a whole question).
"export the loans to excel" or "export my salaries 2026" are data questions and go through the normal pipeline
(their own answer then gets the links), and so is any other real question, even one the router cannot compute."""

from __future__ import annotations

from typing import Any

from .document import strip_export_lines

FOLLOWUP_TOOL = "export_followup"
FOLLOWUP_MAX_WORDS = 5   # words left after the file request is stripped; more than this is a question of its own


def is_pure_followup(routing: Any, understanding: Any, remaining_text: str = "") -> bool:
    """`routing`: query_engine Routing for the message; `understanding`: chat_pipeline Understanding;
    `remaining_text`: the message without its file request (strip_export_terms)."""
    if len(str(remaining_text or "").split()) > FOLLOWUP_MAX_WORDS:
        return False
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
