"""Month/year extraction from free text (shared by AI direct answers)."""

from __future__ import annotations

import re
from datetime import date

_NAME = (
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
_NAME_RE = re.compile(rf"\b{_NAME}\b[\s\-/,.']*(\d{{4}})\b")
_YM_RE = re.compile(r"\b(\d{4})[-/](0?[1-9]|1[0-2])\b")
_MY_RE = re.compile(r"\b(0?[1-9]|1[0-2])[-/](\d{4})\b")
_REL_RE = re.compile(r"\b(this|current|last|previous)\s+month\b")


def _valid(year: int) -> bool:
    return 1990 <= year <= 2100


def find_periods(text: str, today: date | None = None) -> list[tuple[int, int]]:
    """Every (year, month) mentioned: 'Sept-2026', 'January 2026', '2026-09', '09/2026',
    'this month', 'last month'. One entry per mention, in no particular order."""
    q = (text or "").lower()
    out: list[tuple[int, int]] = []
    for m in _NAME_RE.finditer(q):
        year = int(m.group(2))
        if _valid(year):
            out.append((year, _MONTHS.index(m.group(1)[:3]) + 1))
    for m in _YM_RE.finditer(q):
        if _valid(int(m.group(1))):
            out.append((int(m.group(1)), int(m.group(2))))
    for m in _MY_RE.finditer(q):
        if _valid(int(m.group(2))):
            out.append((int(m.group(2)), int(m.group(1))))
    for m in _REL_RE.finditer(q):
        if today is None:
            from django.utils import timezone

            today = timezone.localdate()
        year, month = today.year, today.month
        if m.group(1) in ("last", "previous"):
            year, month = (year - 1, 12) if month == 1 else (year, month - 1)
        out.append((year, month))
    return out
