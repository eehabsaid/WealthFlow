"""Does the user want a downloadable file, and in which formats? Deterministic, no LLM, en / ar / fr / de.

A format word ("excel", "pdf", "word"...) is itself a file request. A bare "export" / "download" with no
format offers the registry's default formats. Questions about HOW to export ("how do I export my data")
are explanations, not file requests, so they never get links.
"""

from __future__ import annotations

import re

from ..query_engine.lexicon import norm
from .registry import ExportFormat, all_formats, default_formats

_GENERIC = re.compile(
    r"\bexport\w*|\bdownload\w*|\bsave (?:it |this |that |them )?as\b|"
    r"تصدير|صدر\w*|تحميل|حمل\w*|نزل\w*|"
    r"\bexporte[rz]?\b|\bt[eé]l[eé]charg\w*|\benregistre\w* (?:en|sous)\b|"
    r"\bexportier\w*|\bherunterlad\w*|\bspeichern als\b"
)
_HOW_TO = re.compile(
    r"\bhow (?:do|can|could|would|to|should)\b|\bwhere (?:do|can|is|are)\b|\bwhat is the way\b|"
    r"كيف|ازاي|اين|فين|"
    r"\bcomment\b|\bo[uù] (?:puis|peut|est)\b|\bwie\b|\bwo (?:kann|finde)\b"
)


def _matches(fmt: ExportFormat, q: str, weak: bool) -> bool:
    return any(re.search(p, q) for p in (fmt.weak_terms if weak else fmt.terms))


def formats_in(text: str) -> list[ExportFormat]:
    q = norm(text)
    return [f for f in all_formats() if _matches(f, q, False)]


def strip_export_terms(text: str) -> str:
    """The question without its file request ("... and export it in excel sheet" -> "... and it in sheet"), for the
    query-engine router: words like "save" in "save it as csv" would otherwise make a plain data lookup look
    like advice and send it to the model."""
    q = norm(text)
    for pattern in (_GENERIC.pattern, *(p for f in all_formats() for p in (*f.terms, *f.weak_terms))):
        q = re.sub(pattern, " ", q)
    return re.sub(r"\s+", " ", q).strip(" ,;.-")


def detect(text: str) -> list[ExportFormat]:
    """Formats to offer for this message, in display order; [] when no file is wanted."""
    q = norm(text)
    if not q or _HOW_TO.search(q):
        return []
    wanted = _GENERIC.search(q) is not None
    named = [f for f in all_formats() if _matches(f, q, False) or ((wanted or formats_in(q)) and _matches(f, q, True))]
    if named:
        return named
    return default_formats() if wanted else []


def exports_enabled_formats(keys: list) -> list[ExportFormat]:
    """Registered formats for `keys` (de-duplicated, display order), [] while file generation is switched off."""
    from .settings import exports_enabled

    wanted = {str(k or "").strip().lower() for k in keys}
    return [f for f in all_formats() if f.key in wanted] if exports_enabled() else []


def requested(text: str) -> list[ExportFormat]:
    """detect() unless file generation is switched off in Settings > AI Advisor (then nothing is offered)."""
    from .settings import exports_enabled

    return detect(text) if exports_enabled() else []
