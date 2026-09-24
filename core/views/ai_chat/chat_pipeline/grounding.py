"""Deterministic numeric grounding: do the figures in an answer trace back to the evidence?

Pure functions, no Django, no LLM. Used by the Validate stage (and by Understand
to pull amounts out of the question).

A figure counts as grounded when it appears in the evidence text within rounding
tolerance, or is a simple derivation of evidence values (a sum/difference of two
values, or a percentage share of one value in another) — models legitimately
compute those and we must not flag them.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")
_NUM_RE = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\s?(%|k\b|m\b|bn\b|b\b|thousand\b|million\b|billion\b)?",
    re.IGNORECASE,
)
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*•]\s*)?\d{1,2}[.)]\s", re.MULTILINE)
_MULT = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9}
_MAX_DERIVED_POOL = 2000


@dataclass(frozen=True)
class Figure:
    raw: str
    value: float          # absolute value, suffix (k/m/bn) applied
    tol: float            # accepted absolute deviation (one unit of the shown precision)
    is_percent: bool
    is_integer: bool


def normalize_digits(text: str) -> str:
    return (text or "").translate(_ARABIC_DIGITS)


def extract_figures(text: str) -> list[Figure]:
    """Every numeric figure in `text`, sign ignored, list markers ('1.') excluded."""
    text = normalize_digits(text)
    marker_spans = {m.start() for m in _LIST_MARKER_RE.finditer(text)}
    out: list[Figure] = []
    for m in _NUM_RE.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        if line_start in marker_spans and text[line_start:m.start()].strip(" -*•") == "":
            continue
        whole, frac, suffix = m.group(1).replace(",", ""), m.group(2), (m.group(3) or "").lower()
        decimals = len(frac) if frac else 0
        mult = _MULT.get(suffix, 1.0)
        value = float(f"{whole}.{frac}" if frac else whole) * mult
        out.append(Figure(
            raw=m.group(0).strip(), value=value, tol=(10 ** -decimals) * mult,
            is_percent=suffix == "%", is_integer=decimals == 0 and not suffix,
        ))
    return out


def checkable_figures(answer: str, question: str) -> list[Figure]:
    """Figures worth checking: drops small integers (dates/list counts), bare years,
    and anything the user already wrote in their own question."""
    asked = [f.value for f in extract_figures(question)]
    keep: list[Figure] = []
    for f in extract_figures(answer):
        if f.is_integer and not f.is_percent and (f.value <= 31 or 1990 <= f.value <= 2100):
            continue
        if any(abs(f.value - a) <= f.tol for a in asked):
            continue
        keep.append(f)
    return keep


class EvidenceIndex:
    """Sorted evidence values for tolerance lookups."""

    def __init__(self, evidence_text: str):
        seen: dict[float, None] = {}
        for f in extract_figures(evidence_text):
            seen.setdefault(round(f.value, 6), None)
        self.values = sorted(seen)
        self._pool = list(seen)[:_MAX_DERIVED_POOL]  # appearance order = priority order

    def __len__(self) -> int:
        return len(self.values)

    def has(self, target: float, tol: float) -> bool:
        i = bisect.bisect_left(self.values, target - tol - 1e-9)
        return i < len(self.values) and self.values[i] <= target + tol + 1e-9

    def has_sum_or_diff(self, target: float, tol: float) -> str | None:
        for a in self._pool:
            if self.has(target - a, tol):
                return "derived_sum"
            if self.has(target + a, tol) or self.has(a - target, tol):
                return "derived_diff"
        return None

    def has_ratio(self, pct: float, tol: float) -> bool:
        """pct ≈ 100*a/b for some evidence values a, b."""
        if pct <= 0:
            return False
        for a in self._pool:
            if a <= 0:
                continue
            b = 100.0 * a / pct
            if self.has(b, b * (tol / pct) + 1e-6):
                return True
        return False


def check_figure(fig: Figure, index: EvidenceIndex) -> str | None:
    """Return how the figure is grounded ('exact', 'derived_*', ...) or None if it isn't."""
    if index.has(fig.value, fig.tol):
        return "exact"
    if fig.is_percent:
        if index.has(fig.value / 100.0, fig.tol / 100.0):
            return "fraction"
        if index.has_ratio(fig.value, fig.tol):
            return "derived_ratio"
    return index.has_sum_or_diff(fig.value, fig.tol)


@dataclass(frozen=True)
class GroundingReport:
    checked: int
    ungrounded: tuple[str, ...]
    methods: dict

    @property
    def ok(self) -> bool:
        return not self.ungrounded


def ground_answer(answer: str, question: str, evidence_text: str) -> GroundingReport:
    figures = checkable_figures(answer, question)
    index = EvidenceIndex(evidence_text)
    methods: dict[str, int] = {}
    bad: list[str] = []
    for fig in figures:
        how = check_figure(fig, index)
        if how:
            methods[how] = methods.get(how, 0) + 1
        elif fig.raw not in bad:
            bad.append(fig.raw)
    return GroundingReport(checked=len(figures), ungrounded=tuple(bad), methods=methods)
