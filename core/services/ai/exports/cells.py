"""Typed table cells: "87,643.86 EGP" -> 87643.86 with the unit moved to the column header, so Excel / CSV
get real numbers (sortable, summable) while Word / PDF / TXT keep the text exactly as the answer shows it."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .document import Block, is_bold_cell, plain

_NUMBER = re.compile(r"^(?P<sign>[+-]?)\s*(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?P<unit>%|[A-Za-z]{1,8})?$")


@dataclass
class TypedTable:
    header: list[str]
    rows: list[list]                  # float for numeric columns, str otherwise
    bold: list[bool]                  # per row
    decimals: list[int]               # per column (0 for text columns)
    numeric: list[bool]               # per column


def parse_number(text: str) -> tuple[float, str, int] | None:
    """(value, unit, decimals) or None when the cell is not a plain number with an optional unit."""
    m = _NUMBER.match(plain(text))
    if not m:
        return None
    num = m["num"].replace(",", "")
    value = float(num) * (-1 if m["sign"] == "-" else 1)
    return value, m["unit"] or "", len(num.split(".")[1]) if "." in num else 0


def typed_table(block: Block) -> TypedTable:
    width = len(block.header) if block.header else max((len(r) for r in block.rows), default=0)
    header = [plain(h) for h in block.header] or [""] * width
    numeric, units, decimals = [], [], []
    for c in range(width):
        parsed = [parse_number(r[c]) for r in block.rows if c < len(r) and plain(r[c])]
        ok = bool(parsed) and all(parsed)
        cell_units = {p[1] for p in parsed if p} if ok else set()
        ok = ok and len(cell_units) == 1
        numeric.append(ok)
        units.append(next(iter(cell_units)) if ok else "")
        decimals.append(max((p[2] for p in parsed if p), default=0) if ok else 0)
    for c in range(width):
        if numeric[c] and units[c]:
            header[c] = f"{header[c]} ({units[c]})" if header[c] else units[c]
    rows, bold = [], []
    for r in block.rows:
        rows.append([parse_number(r[c])[0] if numeric[c] and plain(r[c]) else plain(r[c]) for c in range(width)])
        bold.append(any(is_bold_cell(x) for x in r))
    return TypedTable(header, rows, bold, decimals, numeric)
