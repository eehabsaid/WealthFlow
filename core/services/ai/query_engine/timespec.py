"""Time understanding for the router: months, ranges ('Jun to Sept 2026'), years, relative
periods, 'latest' / 'today', in English and Arabic. Deterministic; no LLM."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .lexicon import rx

MAX_MONTHS = 36
_EN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
_AR = {"يناير": 1, "فبراير": 2, "مارس": 3, "ابريل": 4, "مايو": 5, "يونيو": 6, "يوليو": 7, "اغسطس": 8, "سبتمبر": 9,
       "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12, "كانون الثاني": 1, "شباط": 2, "اذار": 3, "نيسان": 4, "ايار": 5,
       "حزيران": 6, "تموز": 7, "ايلول": 9, "تشرين الاول": 10, "تشرين الثاني": 11, "كانون الاول": 12}
_EN_NAMES = (r"january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|"
             r"september|sept|sep|october|oct|november|nov|december|dec")
_AR_NAMES = "|".join(sorted(_AR, key=len, reverse=True))
MON = rf"(?:{_EN_NAMES}|{_AR_NAMES})"
YEAR = r"(?:19|20)\d\d"
_SEP = r"[\s,./\-']*"
_TO = r"(?:to|until|through|thru|till|-|–|—|الي|حتي|لغايه)"
_RANGE_TO = rx(rf"(?<![\w]){{}}(?P<m1>{MON}){_SEP}(?P<y1>{YEAR})?\s*{_TO}\s*(?P<m2>{MON}){_SEP}(?P<y2>{YEAR})?(?!\w)".replace("{}", ""))
_RANGE_BETWEEN = rx(rf"between\s+(?P<m1>{MON}){_SEP}(?P<y1>{YEAR})?\s*(?:and|&)\s*(?P<m2>{MON}){_SEP}(?P<y2>{YEAR})?(?!\w)")
_RANGE_NUM = rx(rf"(?P<y1>{YEAR})[-/](?P<m1>0?[1-9]|1[0-2])\s*(?:to|until|through|thru|till|-|–|الي|حتي)\s*(?P<y2>{YEAR})[-/](?P<m2>0?[1-9]|1[0-2])(?!\d)")
_NAME_YEAR = rx(rf"(?<![\w])(?P<m>{MON}){_SEP}(?P<y>{YEAR})(?!\d)")
_YM = rx(rf"(?<!\d)(?P<y>{YEAR})[-/](?P<m>0?[1-9]|1[0-2])(?![\d])")
_MY = rx(rf"(?<!\d)(?P<m>0?[1-9]|1[0-2])[-/](?P<y>{YEAR})(?!\d)")
_BARE = rx(rf"(?<![\w])(?P<pre>in|for|of|during|from|to|until|through|since|between|and|في|خلال|عن|لشهر|شهر)?\s*(?P<m>{MON})(?![\w])")
_YEAR_ONLY = rx(rf"(?:\b(?:in|for|of|during|year|throughout|across|all of)|سنه|عام|في|خلال|لعام|طوال)\s*(?P<y>{YEAR})(?!\d)")
_REL_MONTH = rx(r"\b(this|current|last|previous)\s+month\b|الشهر (?:ده|دا|هذا|الحالي|الجاري)|هذا الشهر|الشهر (?:الماضي|السابق|اللي فات)|الشهر اللي فات")
_REL_YEAR = rx(r"\b(this|current|last|previous)\s+year\b|(?:السنه|العام) (?:دي|هذه|هذا|الحاليه|الحالي)|(?:السنه|العام) (?:الماضيه|الماضي|اللي فاتت|السابقه)")
_LAST_N_MONTHS = rx(r"\b(?:last|past|previous)\s+(\d{1,2})\s+months?\b|اخر\s+(\d{1,2})\s+(?:شهر|اشهر|شهور)")
_TODAY = rx(r"\b(today|now|right now|currently|as of now|current)\b|النهارده|النهارده|اليوم|الان|حاليا|دلوقتي")
_LATEST = rx(r"\b(latest|last|most recent|newest|recent)\b|اخر|اخير|احدث")


@dataclass
class TimeSpec:
    kind: str = "none"                       # none | months | latest
    months: list[tuple[int, int]] = field(default_factory=list)
    today: bool = False
    notes: list[str] = field(default_factory=list)   # assumptions made (traced)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "months": [f"{y}-{m:02d}" for y, m in self.months], "today": self.today, "notes": self.notes}


def _mon(word: str) -> int:
    w = word.strip().lower()
    return _AR.get(w) or _EN[w[:3]]


def _shift(y: int, m: int, delta: int) -> tuple[int, int]:
    idx = y * 12 + (m - 1) + delta
    return idx // 12, idx % 12 + 1


def _expand(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
    if a > b:
        a, b = b, a
    out, cur = [], a
    while cur <= b and len(out) <= MAX_MONTHS:
        out.append(cur)
        cur = _shift(*cur, 1)
    return out


def _assume_year(m: int, today: date) -> int:
    return today.year if m <= today.month else today.year - 1


def _blank(q: str, span: tuple[int, int]) -> str:
    return q[: span[0]] + " " * (span[1] - span[0]) + q[span[1]:]


def parse_time(q: str, today: date | None = None) -> TimeSpec:
    """`q` must already be normalised (lexicon.norm)."""
    if today is None:
        from django.utils import timezone
        today = timezone.localdate()
    spec, months = TimeSpec(), set()

    def range_hit(m, numeric=False):
        if numeric:
            a, b = (int(m["y1"]), int(m["m1"])), (int(m["y2"]), int(m["m2"]))
        else:
            m1, m2 = _mon(m["m1"]), _mon(m["m2"])
            y2 = int(m["y2"]) if m["y2"] else (int(m["y1"]) if m["y1"] else _assume_year(m2, today))
            y1 = int(m["y1"]) if m["y1"] else (y2 - 1 if m1 > m2 else y2)
            if not m["y1"] and not m["y2"]:
                spec.notes.append("range_year_assumed")
            a, b = (y1, m1), (y2, m2)
        months.update(_expand(a, b))

    for pat, numeric in ((_RANGE_NUM, True), (_RANGE_TO, False), (_RANGE_BETWEEN, False)):
        for m in list(pat.finditer(q)):
            range_hit(m, numeric)
            q = _blank(q, m.span())
    for m in list(_NAME_YEAR.finditer(q)):
        months.add((int(m["y"]), _mon(m["m"])))
        q = _blank(q, m.span())
    for pat in (_YM, _MY):
        for m in list(pat.finditer(q)):
            months.add((int(m["y"]), int(m["m"])))
            q = _blank(q, m.span())
    for m in list(_BARE.finditer(q)):
        mon = _mon(m["m"])
        if m["m"].strip().lower() == "may" and not m["pre"]:
            continue  # the verb, not the month
        months.add((_assume_year(mon, today), mon))
        spec.notes.append("month_year_assumed")
        q = _blank(q, m.span())
    for m in list(_YEAR_ONLY.finditer(q)):
        months.update((int(m["y"]), i) for i in range(1, 13))
        q = _blank(q, m.span())
    for m in list(_REL_YEAR.finditer(q)):
        last = bool(re.search(r"last|previous|الماضي|فاتت|السابق", m.group(0)))
        months.update((today.year - (1 if last else 0), i) for i in range(1, 13))
        q = _blank(q, m.span())
    for m in list(_REL_MONTH.finditer(q)):
        last = bool(re.search(r"last|previous|الماضي|السابق|فات", m.group(0)))
        months.add(_shift(today.year, today.month, -1 if last else 0))
        q = _blank(q, m.span())
    for m in list(_LAST_N_MONTHS.finditer(q)):
        n = min(int(m.group(1) or m.group(2)), MAX_MONTHS)
        months.update(_shift(today.year, today.month, -i) for i in range(n))
        spec.notes.append("last_n_months_includes_current")
        q = _blank(q, m.span())
    if not months:
        for m in re.finditer(rf"(?<![\d/-])({YEAR})(?![\d/-])", q):
            months.update((int(m.group(1)), i) for i in range(1, 13))
    if months:
        spec.kind, spec.months = "months", sorted(months)[:MAX_MONTHS] if len(months) <= MAX_MONTHS else sorted(months)[-MAX_MONTHS:]
        return spec
    spec.today = bool(_TODAY.search(q))
    if _LATEST.search(q) or spec.today:
        spec.kind = "latest"
    return spec
