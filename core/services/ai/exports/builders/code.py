"""Text and code files (.md .py .js .html .css .json .sql): the file is the answer's code, never executed or evaluated.

The raw text comes from the `generate_file` content, else the answer's fenced code block of that language, else the whole
answer. A table-only answer becomes json / sql / md rows."""

from __future__ import annotations

import json

from ..cells import typed_table
from ..document import ExportDocument, plain
from ..full_data import code_from_markdown
from ..registry import ExportFormat, register
from .guide_html import build_guide_html, is_guide


def _rows_as_dicts(doc: ExportDocument) -> list[dict]:
    out = []
    for block in doc.tables():
        table = typed_table(block)
        out += [dict(zip(table.header, r)) for r in table.rows]
    return out


def _sql(doc: ExportDocument) -> str:
    lines = []
    for block in doc.tables():
        table = typed_table(block)
        quote = lambda v: "NULL" if v == "" else (str(v) if isinstance(v, (int, float)) else "'" + str(v).replace("'", "''") + "'")   # noqa: E731
        lines += [f'INSERT INTO "export" ({", ".join(chr(34) + h + chr(34) for h in table.header)}) VALUES ({", ".join(quote(v) for v in r)});' for r in table.rows]
    return "\n".join(lines) + "\n"


def _builder(ext: str):
    def build(doc: ExportDocument, lang: str) -> bytes:
        if ext == "html" and is_guide(doc):   # a user guide / manual: the styled single-page guide with its contents rail
            return build_guide_html(doc, lang)
        has_code = "```" in doc.source or ext in ("md",)
        if ext == "json" and doc.tables() and not has_code:
            text = json.dumps(_rows_as_dicts(doc), ensure_ascii=False, indent=2, default=str) + "\n"
        elif ext == "sql" and doc.tables() and "INSERT" not in doc.source.upper() and not has_code:
            text = _sql(doc)
        elif ext == "md":
            text = (doc.source if "|" in doc.source or "#" in doc.source else "\n".join(plain(b.text) for b in doc.blocks)).strip() + "\n"
        else:
            text = code_from_markdown(doc.source, ext)
        return text.encode("utf-8")
    return build


for _ext, _mime, _label, _terms in (
    ("py", "text/x-python", "Python (.py)", (r"\.py\b|\bpython (?:file|script)\b|ملف بايثون",)),
    ("js", "text/javascript", "JavaScript (.js)", (r"\.js\b|\bjavascript (?:file|script)\b",)),
    ("html", "text/html", "HTML (.html)", (r"\.html?\b|\bhtml (?:\w+ ){0,2}(?:file|page|guide|document|manual|doc|version|format)\b|\b(?:as|in|to|en|als|im|nach)\s+(?:an?\s+)?html\b|\bhtml-\w+", r"(?:ملف|صفح[ةه]|دليل|صيغ[ةه]|بصيغ[ةه])\s*html\b")),
    ("css", "text/css", "CSS (.css)", (r"\.css\b|\bcss file\b|\bstylesheet\b",)),
    ("json", "application/json", "JSON (.json)", (r"\.json\b|\bjson file\b",)),
    ("sql", "application/sql", "SQL (.sql)", (r"\.sql\b|\bsql (?:file|script)\b",)),
    ("md", "text/markdown", "Markdown (.md)", (r"\.md\b|\bmarkdown (?:file|doc)\b",)),
):
    register(ExportFormat(key=_ext, label=_label, extension=_ext, mime=f"{_mime}; charset=utf-8", builder=_builder(_ext),
                          terms=_terms, offer_by_default=False, order=60))
