"""Download links appended to an answer: one markdown link per format, pointing at the saved message."""

from __future__ import annotations

from django.urls import reverse

from ..query_engine.labels import t
from .registry import ExportFormat

ROUTE_NAME = "ai-message-export"       # defined in core/urls/financial_advisor_urls.py


def export_url(message_id: int, fmt: ExportFormat) -> str:
    return reverse(ROUTE_NAME, args=[message_id, fmt.key])


def links_line(message_id: int, formats: list[ExportFormat], lang: str) -> str:
    """'[Download as Excel (.xlsx)](/api/...) · [Download as PDF (.pdf)](/api/...)'"""
    return " · ".join(f"[{t(lang, 'export_download', format=f.label)}]({export_url(message_id, f)})" for f in formats)


def append_links(content: str, message_id: int, formats: list[ExportFormat], lang: str) -> str:
    return f"{content.rstrip()}\n\n{links_line(message_id, formats, lang)}" if formats else content
