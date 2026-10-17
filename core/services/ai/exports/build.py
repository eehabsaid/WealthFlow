"""AIMessage -> ExportDocument -> file bytes. Owner scoping is the view's job; this module trusts its input."""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from ..query_engine.labels import month_label, t
from ..query_engine.lexicon import language
from .document import ExportDocument, parse_markdown, plain, strip_export_lines
from .full_data import from_question, from_tool_calls
from .registry import ExportFormat


def _today(lang: str) -> str:
    """'13 October 2026' / '13 أكتوبر 2026': month names read correctly in right-to-left text, ISO dates get reordered."""
    today = timezone.localdate()
    return f"{today.day} {month_label(lang, today.year, today.month)}"


def _previous_question(message: Any, question_id: int | None) -> str:
    if question_id is None:
        return ""
    return (message.conversation.messages.filter(role="user", is_deleted=False, id__lt=question_id)
            .order_by("-id").values_list("content", flat=True).first() or "")


def _question_row(message: Any) -> tuple[int | None, str]:
    row = (message.conversation.messages.filter(role="user", is_deleted=False, id__lt=message.id)
           .order_by("-id").values_list("id", "content").first())
    return (row[0], row[1]) if row else (None, "")


def document_for(message: Any) -> ExportDocument:
    """The file's content: the tool dataset specs / the routed question replayed in full, else the saved answer text."""
    user = message.conversation.user
    question_id, question_raw = _question_row(message)
    question = plain(question_raw)
    saved = strip_export_lines(message.content)
    content, source = saved, None
    replay = from_tool_calls(message, user)
    if replay:
        content, source = replay
    else:
        content = from_question(message, user, question_raw, _previous_question(message, question_id)) or saved
    lang = language(question or content)
    if lang == "en":
        lang = language(content)   # an English request for a document written in Arabic: the file follows its own text (right-to-left)
    blocks = parse_markdown(content)
    title, shown_question = t(lang, "export_title"), f"{t(lang, 'export_question')}: {question}" if question else ""
    if blocks and blocks[0].kind == "heading" and blocks[0].level == 1:
        # a self-titled document (a user guide, a report): its own title replaces the generic "WealthFlow AI / Question:" block
        title, shown_question = blocks.pop(0).text, ""
    return ExportDocument(
        title=title, question=shown_question, generated=t(lang, "export_generated", date=_today(lang)),
        lang=lang, blocks=blocks, source=source or saved,
    )


def build_file(message: Any, fmt: ExportFormat) -> tuple[bytes, str]:
    """(file bytes, download file name) for one saved assistant message."""
    doc = document_for(message)
    name = f"WealthFlow_{timezone.localdate():%Y%m%d}_{message.id}.{fmt.extension}"
    return fmt.builder(doc, doc.lang), name
