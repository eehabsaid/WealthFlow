"""Does the user want a downloadable file, and in which formats? Deterministic, no LLM, en / ar / fr / de.

A format word ("excel", "pdf", "word"...) is itself a file request. A bare "export" / "download" with no
format offers the registry's default formats. Questions about HOW to export ("how do I export my data")
are explanations, not file requests, so they never get links.
"""

from __future__ import annotations

import re
from contextvars import ContextVar

from ai.services.query_engine.lexicon import norm
from ai.services.exports.registry import ExportFormat, all_formats, default_formats

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


_FILE_WORDS = re.compile(r"\bfiles?\b|\bdocuments?\b|\breports?\b|\bguides?\b|\bmanuals?\b|ملف|مستند|وثيق|تقرير|دليل|\bfichier|\bdatei")
_resolved: ContextVar = ContextVar("ai_file_intent", default=None)   # {normalised message: format keys} the model decided for THIS request


def set_resolved(text: str, keys) -> None:
    """The model's reading of what files the message asks for (see intent_model.py): detect() returns it for this exact message."""
    _resolved.set({**(_resolved.get() or {}), norm(text): tuple(keys)})


def clear_resolved() -> None:
    _resolved.set(None)


def has_file_word(text: str) -> bool:
    return _FILE_WORDS.search(norm(text)) is not None


def might_want_file(text: str, earlier: tuple = ()) -> bool:
    """Cheap gate for the model question (instant answers keep their 0 model calls). A message that names a file format or says export /
    download qualifies; a plain "file" / "document" / "guide" word qualifies only when an EARLIER message of the chat asked for a file
    ("where is the file?" after a request for a guide), so "which file defines ExpenseService?" never costs a model call."""
    q = norm(text)
    if not q:
        return False
    if _GENERIC.search(q) is not None or any(_matches(f, q, False) or _matches(f, q, True) for f in all_formats()):
        return True
    return _FILE_WORDS.search(q) is not None and any(detect(m) for m in earlier)


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
    hit = (_resolved.get() or {}).get(q)
    if hit is not None:   # the model read the whole message (and the chat before it): its answer wins over the word patterns below
        return [f for f in all_formats() if f.key in hit]
    if not q or _HOW_TO.search(q):
        return []
    wanted = _GENERIC.search(q) is not None
    named = [f for f in all_formats() if _matches(f, q, False) or ((wanted or formats_in(q)) and _matches(f, q, True))]
    if named:
        return named
    return default_formats() if wanted else []


def exports_enabled_formats(keys: list) -> list[ExportFormat]:
    """Registered formats for `keys` (de-duplicated, display order), [] while file generation is switched off."""
    from ai.services.exports.settings import exports_enabled

    wanted = {str(k or "").strip().lower() for k in keys}
    return [f for f in all_formats() if f.key in wanted] if exports_enabled() else []


def requested(text: str) -> list[ExportFormat]:
    """detect() unless file generation is switched off in Settings > AI Advisor (then nothing is offered)."""
    from ai.services.exports.settings import exports_enabled

    return detect(text) if exports_enabled() else []
