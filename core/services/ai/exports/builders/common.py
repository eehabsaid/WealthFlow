"""Layout facts shared by the file builders."""

from __future__ import annotations

from ..document import ExportDocument

WIDE_TABLE_COLUMNS = 7          # a table this wide switches Word / PDF pages to landscape


def is_wide(doc: ExportDocument) -> bool:
    return any(max(len(t.header), *(len(r) for r in t.rows), 0) >= WIDE_TABLE_COLUMNS for t in doc.tables())


def intro_lines(doc: ExportDocument) -> list[tuple[str, str]]:
    """[(role, text)] for the title block: role is 'title', 'question' or 'meta'."""
    return [(role, text) for role, text in (("title", doc.title), ("question", doc.question), ("meta", doc.generated)) if text]


def guide_blocks(doc: ExportDocument) -> list:
    """A guide's blocks without a paragraph that repeats earlier text (Word / PDF; the HTML guide drops the same repeats). Steps,
    bullets, headings and tables are kept."""
    import re

    seen, out = set(), []
    for block in doc.blocks:
        if block.kind == "text" and not re.match(r"^\d+\.\s", block.text):
            key = re.sub(r"\s+", " ", block.text).strip().casefold()
            if not key or key in seen:
                continue
            seen.add(key)
        out.append(block)
    return out
