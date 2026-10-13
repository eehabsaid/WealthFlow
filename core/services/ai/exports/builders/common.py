"""Layout facts shared by the file builders."""

from __future__ import annotations

from ..document import ExportDocument

WIDE_TABLE_COLUMNS = 7          # a table this wide switches Word / PDF pages to landscape


def is_wide(doc: ExportDocument) -> bool:
    return any(max(len(t.header), *(len(r) for r in t.rows), 0) >= WIDE_TABLE_COLUMNS for t in doc.tables())


def intro_lines(doc: ExportDocument) -> list[tuple[str, str]]:
    """[(role, text)] for the title block: role is 'title', 'question' or 'meta'."""
    return [(role, text) for role, text in (("title", doc.title), ("question", doc.question), ("meta", doc.generated)) if text]
