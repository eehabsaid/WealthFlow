"""CSV (.csv, opens in Excel; numbers are real numbers, units in headers) and plain text (.txt)."""

from __future__ import annotations

import csv
from io import StringIO

from ..cells import typed_table
from ..document import ExportDocument, is_bold_cell, plain
from ..registry import ExportFormat, register
from .common import intro_lines

_BOM = "﻿"          # lets Excel read UTF-8 (Arabic, accents) from a .csv


def _build_csv(doc: ExportDocument, lang: str) -> bytes:
    out = StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    for _, text in intro_lines(doc):
        writer.writerow([text])
    for block in doc.blocks:
        if block.kind == "table":
            table = typed_table(block)
            writer.writerow([])
            if any(table.header):
                writer.writerow(table.header)
            for values, decimals in ((r, table.decimals) for r in table.rows):
                writer.writerow([f"{v:.{decimals[i]}f}" if isinstance(v, float) else v for i, v in enumerate(values)])
        else:
            writer.writerow([("• " if block.kind == "bullet" else "") + plain(block.text)])
    return (_BOM + out.getvalue()).encode("utf-8")


def _build_txt(doc: ExportDocument, lang: str) -> bytes:
    lines = [text for _, text in intro_lines(doc)]
    for block in doc.blocks:
        if block.kind == "table":
            lines.append("")
            if block.header:
                lines += [" | ".join(plain(h) for h in block.header), "-+-".join("-" * max(3, len(plain(h))) for h in block.header)]
            lines += [" | ".join((plain(c).upper() if is_bold_cell(c) else plain(c)) for c in r) for r in block.rows]
        elif block.kind == "heading":
            lines += ["", plain(block.text), "=" * max(3, len(plain(block.text)))]
        else:
            lines.append(("- " if block.kind == "bullet" else "") + plain(block.text))
    return ("\n".join(lines) + "\n").encode("utf-8")


register(ExportFormat(
    key="csv", label="CSV (.csv)", extension="csv", mime="text/csv; charset=utf-8", builder=_build_csv, order=40,
    terms=(r"\bcsv\b", r"سي اس في"), offer_by_default=False,
))
register(ExportFormat(
    key="txt", label="Text (.txt)", extension="txt", mime="text/plain; charset=utf-8", builder=_build_txt, order=50,
    terms=(r"\btxt\b|\btext file\b|\bplain text\b|\bfichier texte\b|\btextdatei\b", r"ملف نصي|ملف تكست"), offer_by_default=False,
))
