"""Excel (.xlsx): one "Answer" sheet — title block, then headings / text / bullets / tables in answer order.
Tables get a styled header row, real numeric cells (unit moved to the header), bold total rows, auto widths."""

from __future__ import annotations

import re
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..cells import typed_table
from ..document import ExportDocument, plain
from ..registry import ExportFormat, register

_HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
_MAX_SHEET_TITLE = 31       # Excel's own limit
_BAD_SHEET_CHARS = re.compile(r"[\[\]:*?/\\]")
_MAX_WIDTH = 60
_MIN_WIDTH = 10


def _number_format(decimals: int) -> str:
    return "#,##0" + (f".{'0' * decimals}" if decimals else "")


def _write_table(ws, start: int, block, widths: dict[int, int]) -> int:
    table = typed_table(block)
    row = start
    if any(table.header):
        for c, text in enumerate(table.header, 1):
            cell = ws.cell(row=row, column=c, value=text)
            widths[c] = max(widths.get(c, 0), len(text) + 2)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = _HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        row += 1
    for values, bold in zip(table.rows, table.bold):
        for c, value in enumerate(values, 1):
            cell = ws.cell(row=row, column=c, value=value)
            widths[c] = max(widths.get(c, 0), len(f"{value:,.{table.decimals[c - 1]}f}" if table.numeric[c - 1] else str(value)) + 2)
            if table.numeric[c - 1]:
                cell.number_format = _number_format(table.decimals[c - 1])
            if bold:
                cell.font = Font(bold=True)
        row += 1
    return row


def _build(doc: ExportDocument, lang: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = (_BAD_SHEET_CHARS.sub(" ", plain(doc.title)).strip() or "Sheet1")[:_MAX_SHEET_TITLE]
    ws.sheet_view.rightToLeft = lang == "ar"
    row = 1
    for text, bold in ((doc.title, True), (doc.question, False), (doc.generated, False)):
        if text:
            ws.cell(row=row, column=1, value=text).font = Font(bold=bold, size=14 if bold else 11)
            row += 1
    row += 1 if row > 1 else 0
    widths: dict[int, int] = {}
    for block in doc.blocks:
        if block.kind == "table":
            row = _write_table(ws, row, block, widths) + 1
        elif block.kind == "heading":
            ws.cell(row=row, column=1, value=block.text).font = Font(bold=True, size=12)
            row += 1
        else:
            ws.cell(row=row, column=1, value=("• " if block.kind == "bullet" else "") + plain(block.text))
            row += 1
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = max(_MIN_WIDTH, min(_MAX_WIDTH, width))
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


register(ExportFormat(
    key="xlsx", label="Excel (.xlsx)", extension="xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", builder=_build, order=10,
    terms=(r"\bexcel\b|\bxlsx?\b|\bspreadsheet\b|\bworksheet\b|\btableur\b|\btabellenkalkulation\b|\bexcel-?(?:datei|tabelle)\b",
           r"اكسل|اكسيل|جدول بيانات"),
))
