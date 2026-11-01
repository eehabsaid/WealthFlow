"""Turns an uploaded file into text by CODE (no model). Tables also get the facts the app computes (row count, column totals),
so the model never has to add up numbers itself."""

from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation

MAX_BYTES = 10 * 1024 * 1024
TABLE_EXT = {"csv", "xlsx"}
TEXT_EXT = {"txt", "md", "pdf", "docx"}
IMAGE_EXT = {"png", "jpg", "jpeg", "webp"}
MIME_BY_EXT = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
SHEET_ROWS = 2000          # rows read per sheet; the rest are counted, not read
MAX_CHARS = 400_000        # hard ceiling of stored text; what the model actually gets is cut to its context size later


class AttachmentError(Exception):
    pass


def ext_of(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def kind_of(name: str) -> str:
    e = ext_of(name)
    return "table" if e in TABLE_EXT else "text" if e in TEXT_EXT else "image" if e in IMAGE_EXT else ""


def _num(cell):
    if isinstance(cell, (int, float, Decimal)) and not isinstance(cell, bool):
        return Decimal(str(cell))
    try:
        return Decimal(str(cell).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def _table_text(sheets: dict[str, list[list]], total_rows: dict[str, int]) -> str:
    out = []
    for name, rows in sheets.items():
        if not rows:
            continue
        head = [str(c or "").strip() for c in rows[0]]
        body = rows[1:]
        out.append(f"## {name}: {total_rows[name] - 1} data rows, columns: {', '.join(head)}")
        sums = []
        for i, col in enumerate(head):
            nums = [_num(r[i]) for r in body if i < len(r) and r[i] not in (None, "")]
            nums = [n for n in nums if n is not None]
            if nums and len(nums) >= max(1, len(body) // 2):
                sums.append(f"{col}: sum {sum(nums)}, min {min(nums)}, max {max(nums)}, count {len(nums)}")
        if sums:
            out.append("COMPUTED BY THE APP FROM " + ("ALL READ ROWS" if total_rows[name] <= len(rows) else f"THE FIRST {len(rows) - 1} ROWS ONLY (file has {total_rows[name] - 1})") + ": " + "; ".join(sums))
        out.extend(" | ".join("" if c is None else str(c) for c in r) for r in rows)
    return "\n".join(out)


def _csv(raw: bytes) -> str:
    text = raw.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows, total = [], 0
    for r in csv.reader(io.StringIO(text), dialect):
        total += 1
        if len(rows) <= SHEET_ROWS:
            rows.append(r)
    return _table_text({"csv": rows}, {"csv": total})


def _xlsx(raw: bytes) -> str:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    sheets, totals = {}, {}
    for ws in wb.worksheets:
        rows, total = [], 0
        for r in ws.iter_rows(values_only=True):
            total += 1
            if len(rows) <= SHEET_ROWS:
                rows.append(list(r))
        sheets[ws.title], totals[ws.title] = rows, total
    return _table_text(sheets, totals)


def _pdf(raw: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        return "\n\n".join(f"[page {i}]\n{p.extract_text() or ''}" for i, p in enumerate(pdf.pages, 1))


def _docx(raw: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(raw))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for t in doc.tables:
        parts.extend(" | ".join(c.text.strip() for c in row.cells) for row in t.rows)
    return "\n".join(parts)


def extract(name: str, raw: bytes) -> tuple[str, str]:
    """(kind, text). Pictures have no text (the model looks at the bytes). Raises AttachmentError with a plain reason."""
    kind = kind_of(name)
    if not kind:
        raise AttachmentError("unsupported_type")
    if len(raw) > MAX_BYTES:
        raise AttachmentError("too_large")
    e = ext_of(name)
    try:
        if kind == "image":
            return kind, ""
        text = {"csv": _csv, "xlsx": _xlsx, "pdf": _pdf, "docx": _docx}.get(e, lambda b: b.decode("utf-8", errors="replace"))(raw)
    except Exception:
        raise AttachmentError("unreadable") from None
    text = text.strip()
    if not text:
        raise AttachmentError("empty")
    return kind, text[:MAX_CHARS]
