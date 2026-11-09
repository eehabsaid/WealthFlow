"""Language-independent helpers: figures found in a text and the writing system of a text. No word lists, no per-language regexes."""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation

_DIGITS = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")} | {ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")}
_DATE = re.compile(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}")
_MARKER = re.compile(r"(?m)^\s*(?:[-*•]|\d{1,3}[.)])\s+")
_NUMBER = re.compile(r"\d[\d,.٬٫   ]*\d|\d")


def _variants(token: str) -> set[Decimal]:
    """Every sensible reading of one printed figure ('1,234.5', '1.234,5', '12.500'); a figure matches if ANY reading matches."""
    token = token.replace(" ", " ").replace(" ", " ").replace("٬", ",").replace("٫", ".").strip()
    token = re.sub(r"(?<=\d) (?=\d{3}\b)", "", token)
    seps = [c for c in token if c in ",."]
    readings = set()
    if not seps:
        readings.add(token)
    else:
        last = max(token.rfind(","), token.rfind("."))
        whole, frac = token[:last], token[last + 1:]
        readings.add(re.sub(r"[,.]", "", whole) + "." + frac)            # the last separator is the decimal point
        if len(frac) == 3 or len(set(seps)) == 1 and len(seps) > 1:
            readings.add(re.sub(r"[,.]", "", token))                       # or every separator groups thousands
    out = set()
    for r in readings:
        try:
            out.add(Decimal(r))
        except InvalidOperation:
            continue
    return out


def figures(text: str, *, skip_dates: bool = True) -> list[tuple[str, set[Decimal]]]:
    """[(printed, readings)] for each figure in `text`. Dates and list numbering are not figures."""
    clean = str(text or "").translate(_DIGITS)
    if skip_dates:
        clean = _DATE.sub(" ", clean)
    clean = _MARKER.sub("", clean)
    return [(m.group(0).strip(), v) for m in _NUMBER.finditer(clean) if (v := _variants(m.group(0)))]


def close(a: Decimal, b: Decimal, printed: str = "") -> bool:
    """Equal at the precision printed: whole numbers may be rounded (+-0.5), decimals must be right to the cent."""
    tolerance = Decimal("0.5") if re.fullmatch(r"\d[\d,]*", printed or "") else Decimal("0.0051")
    return abs(a - b) <= tolerance


def appears(printed: str, readings: set[Decimal], pool: set[Decimal]) -> bool:
    return any(close(r, p, printed) for r in readings for p in pool)


def pool_of(text: str) -> set[Decimal]:
    """Every figure in a tool-result text, including all of its readings."""
    return {v for _, vs in figures(text, skip_dates=False) for v in vs}


def script_of(text: str) -> str:
    """Dominant writing system of a text (ARABIC, LATIN, CYRILLIC, CJK...): the only language signal that needs no word list.
    Latin-script languages (English / French / German) are NOT told apart."""
    counts: dict[str, int] = {}
    for ch in str(text or ""):
        if ch.isalpha():
            name = unicodedata.name(ch, "").split(" ")[0]
            counts[name] = counts.get(name, 0) + 1
    return max(counts, key=counts.get) if counts else ""
