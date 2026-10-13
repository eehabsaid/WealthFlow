"""AIMessage -> ExportDocument -> file bytes. Owner scoping is the view's job; this module trusts its input."""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from ..query_engine.labels import month_label, t
from ..query_engine.lexicon import language
from .document import ExportDocument, parse_markdown, plain, strip_export_lines
from .registry import ExportFormat


def _today(lang: str) -> str:
    """'13 October 2026' / '13 أكتوبر 2026': month names read correctly in right-to-left text, ISO dates get reordered."""
    today = timezone.localdate()
    return f"{today.day} {month_label(lang, today.year, today.month)}"


def _question_for(message: Any) -> str:
    previous = (message.conversation.messages.filter(role="user", is_deleted=False, id__lt=message.id)
                .order_by("-id").values_list("content", flat=True).first())
    return plain(previous or "")


def document_for(message: Any) -> ExportDocument:
    content = strip_export_lines(message.content)
    question = _question_for(message)
    lang = language(question or content)
    return ExportDocument(
        title=t(lang, "export_title"),
        question=f"{t(lang, 'export_question')}: {question}" if question else "",
        generated=t(lang, "export_generated", date=_today(lang)),
        lang=lang, blocks=parse_markdown(content),
    )


def build_file(message: Any, fmt: ExportFormat) -> tuple[bytes, str]:
    """(file bytes, download file name) for one saved assistant message."""
    doc = document_for(message)
    name = f"WealthFlow_{timezone.localdate():%Y%m%d}_{message.id}.{fmt.extension}"
    return fmt.builder(doc, doc.lang), name
