"""Last resort of the guide translation: a piece that the chunk and the piece translations could not produce is translated line by line.

One line at a time the model cannot lose a paragraph, merge two steps or change a heading level (the checks that reject a big
chunk), so a guide asked for in Arabic no longer keeps a whole English chapter because one long reply was refused twice. The
Markdown marker of a line (#, -, 1.) is kept by the app and only the text after it is translated."""

from __future__ import annotations

import logging
import re
import time

from ai.services.investigation.refusal import is_refusal

logger = logging.getLogger(__name__)
MARKER = re.compile(r"^(\s*(?:#{1,6}|[-*•]|\d+[.)])\s+)(.*)$")
HAS_WORDS = re.compile(r"[^\W\d_]{2,}")
MAX_UNCHANGED_WORDS = 2     # a one or two word line (a product or feature name) may legitimately stay as it is
TEMPERATURES = (0.1, 0.4, 0.7)
LINE_SYSTEM = ("Translate the text the user sends into {language}. It is one line of a user guide for the WealthFlow app. "
               "Leave product names (WealthFlow), file names, URLs, numbers and currency codes unchanged. A quoted button, tab or menu "
               "name inside a sentence: translate it and keep the original in parentheses. "
               "Reply with the translation only: one line, no comments, no Markdown markers.")


def _accepted(source: str, text: str, cut: bool, non_latin: bool) -> bool:
    from ai.services.investigation.compose_translate import latin_share

    if cut or not text.strip() or "\n" in text.strip() or is_refusal(text, True):
        return False
    if re.sub(r"\W+", "", text.lower()) == re.sub(r"\W+", "", source.lower()):
        return len(source.split()) <= MAX_UNCHANGED_WORDS
    return not (non_latin and latin_share(text) > 0.9)


def _line(ask, cut, system: str, line: str, non_latin: bool, deadline: float) -> str:
    marker, text = (m.group(1), m.group(2)) if (m := MARKER.match(line)) else ("", line.strip())
    for temperature in TEMPERATURES:
        if time.monotonic() > deadline - 20:
            return ""
        got = ask(system, text, temperature).strip()
        if _accepted(text, got, cut(), non_latin):
            return marker + (MARKER.sub(r"\2", got) if marker else got)   # the model must not add a second marker
    return ""


def translate_lines(ask, cut, language: str, piece: str, non_latin: bool, deadline: float) -> tuple[str, int]:
    """(the piece translated line by line, how many lines stayed English)."""
    system, out, left = LINE_SYSTEM.format(language=language), [], 0
    for line in piece.splitlines():
        if not HAS_WORDS.search(line) or line.lstrip().startswith("!["):
            out.append(line)
            continue
        got = _line(ask, cut, system, line, non_latin, deadline)
        left += 0 if got else 1
        out.append(got or line)
    if left:
        logger.warning("[AI-TRANSLATE] %d line(s) stayed English: %.60s", left, piece.strip().replace("\n", " "))
    return "\n".join(out), left
