"""A guide in another language: written in English first (the app's own knowledge is English, and a model that writes a long
guide straight into Arabic drifts back to English paragraph by paragraph), then translated chunk by chunk.

Everything is structural, no phrase or language lists: the model names the language in one word, the Markdown is cut at the
guide's own "## " / "### " headings, each chunk is translated alone, and a translation is only accepted when it is complete:
not cut off by the output-token limit, not empty / unchanged / refused, headings kept and, for a language with its own alphabet,
really written in that alphabet. A rejected chunk is retried in smaller pieces; only a piece that still fails stays English, so
the guide never has a hole. `ask(system, user_content, temperature) -> str` is the composer's model call and `cut()` says
whether its last reply was stopped by the output limit."""

from __future__ import annotations

import logging
import re
import time

from core.services.ai.protocol import log_reply, parse_yes_no

from .refusal import is_refusal

logger = logging.getLogger(__name__)

CHUNK_CHARS, PIECE_CHARS = 2200, 900
MAX_COPIED_SHARE, MIN_WORDS_TO_JUDGE = 0.6, 12   # share of a translation's words copied from the source = untranslated (any language)
MIN_PARAGRAPHS, MIN_KEPT_PARAGRAPHS = 4, 0.8   # a translation keeps at least this share of the source's prose lines
MAX_LATIN_SHARE = 0.5     # a translation into a non-Latin language may keep product names / quoted labels, not whole sentences
_LANGUAGE_Q = ("Answer with one word only: the language the requested document must be written in. Use the language the request "
               "names; if it names none, the language the request itself is written in. Reply with the language's English name "
               "(for example English, Arabic, French) and nothing else.")
_NAMED_Q = ("Answer YES or NO only. Does the request below explicitly ask for the document to be written in {language}? Answer NO when "
            "the request only happens to be written in another language or names no language at all.")
_LATIN_Q = "Answer YES or NO only. Is {language} normally written in the Latin alphabet (like English, French or German)?"
_TRANSLATE = ("You are a professional translator. Translate the Markdown the user sends into {language}.\n"
              "- Keep the Markdown structure exactly: the same headings with the same number of # (#, ##, ###, ####), bullet and numbered lists, blank lines.\n"
              "- Translate every heading, sentence and list item; leave no English sentence behind.\n"
              "- Leave product names (WealthFlow), file names, URLs, code, numbers and currency codes unchanged.\n"
              "- A quoted button, tab or menu name inside a sentence or step: translate it and keep the original in parentheses. "
              "A heading is translated only, without the original in parentheses.\n"
              "- Keep every paragraph and list item: one translated line for each source line, never drop or merge a sentence.\n"
              "- Translate the same English term the same way everywhere in the text.\n"
              "Reply with the translation only, without comments.")


def target_language(ask, user_text: str) -> str:
    """The language the document must be in, or "" for English / when the answer is not a language name."""
    word = ask(_LANGUAGE_Q, user_text, 0).strip().strip(".\"'`*").split("\n")[0].strip()
    if not word or len(word) > 24 or not all(ch.isalpha() or ch in " -" for ch in word) or word.lower().startswith("english"):
        return ""
    raw = ask(_NAMED_Q.format(language=word), user_text, 0)   # a one-word answer can be wrong (an English request came back as Arabic): confirmed once
    named = parse_yes_no(raw)
    log_reply("language_named", raw, named)
    return word if named is not False else ""


def uses_latin_script(ask, language: str) -> bool:
    return ask(_LATIN_Q.format(language=language), language, 0).strip().upper().startswith("YES")


def _without_originals(text: str) -> str:
    """The text without what may legitimately stay in the source language: code, URLs and the original name that the
    translation keeps in parentheses after a translated button / tab / menu name."""
    return re.sub(r"\([^()]*\)", " ", re.sub(r"```.*?```|`[^`]*`|https?://\S+", " ", text, flags=re.S))


def latin_share(text: str) -> float:
    letters = [ch for ch in _without_originals(text) if ch.isalpha()]
    return sum(1 for ch in letters if ch.isascii()) / len(letters) if letters else 1.0


def _words(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]{3,}", _without_originals(text).casefold())


def copied_share(source: str, text: str) -> float:
    """Share of the translation's words that also occur in the source. Works for every language and script: a real translation
    shares few words with the English source (names, cognates), a reply that is still English shares most of them."""
    words = _words(text)
    if len(words) < MIN_WORDS_TO_JUDGE:
        return 0.0
    known = set(_words(source))
    return sum(1 for w in words if w in known) / len(words)


def _pack(pieces: list[str], limit: int) -> list[str]:
    chunks, cur = [], ""
    for piece in pieces:
        if cur and len(cur) + len(piece) > limit:
            chunks.append(cur)
            cur = ""
        cur += piece
    return chunks + ([cur] if cur.strip() else [])


def split_chunks(markdown: str, limit: int = CHUNK_CHARS) -> list[str]:
    """Pieces of at most ~`limit` characters cut at "## " sections, then "### " parts, then lines; joined back they are the
    original text."""
    out = []
    for section in re.split(r"(?m)^(?=## )", markdown):
        if len(section) <= limit:
            out.append(section)
            continue
        for part in _pack(re.split(r"(?m)^(?=### )", section), limit):
            out.extend([part] if len(part) <= limit else _pack(re.split(r"(?<=\n)", part), limit))
    return [c for c in out if c.strip()]


def _paragraphs(text: str) -> int:
    """The prose lines of a text: not headings, not list items, not blank."""
    return sum(1 for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("#", "-", "*", "\u2022")) and not re.match(r"\s*\d+[.)]\s", line))


def clean_headings(text: str) -> str:
    """A translated heading without the English name some translators append in parentheses (steps keep theirs, headings never)."""
    return re.sub(r"(?m)^(\s*#+\s[^\n]*?[^\W\d_][^\n]*?)\s*\([A-Za-z][^()\n]*\)\s*$",
                  lambda m: m.group(1) if re.search(r"[^\x00-\x7f]", m.group(1)) else m.group(0), text)


def _headings(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.lstrip().startswith("#"))


def rejection(source: str, text: str, cut: bool, non_latin: bool) -> str:
    """Why a translation is not accepted (\"\" when it is): the reason is logged so a piece left in English can be explained."""
    if cut:
        return "cut off by the output limit"
    if not text or len(text) < 0.4 * len(source):
        return "empty or much shorter than the source"
    if is_refusal(text, True):
        return "refusal"
    if re.sub(r"\W+", "", text.lower()) == re.sub(r"\W+", "", source.lower()):
        return "returned unchanged"
    if non_latin and latin_share(text) > MAX_LATIN_SHARE:
        return "still mostly English (alphabet)"
    if copied_share(source, text) > MAX_COPIED_SHARE:
        return "still mostly the source language (copied words)"   # also for languages written in the same alphabet (French, German...)
    if _paragraphs(source) >= MIN_PARAGRAPHS and _paragraphs(text) < MIN_KEPT_PARAGRAPHS * _paragraphs(source):
        return "paragraphs lost"   # a purpose sentence dropped under a heading is not noticed by the other checks
    return "" if abs(_headings(text) - _headings(source)) <= max(1, _headings(source) // 3) else "headings lost or added"


def acceptable(source: str, text: str, cut: bool, non_latin: bool) -> bool:
    return not rejection(source, text, cut, non_latin)


def restore_levels(source: str, text: str) -> str:
    """The translation with the heading levels of the source: a translator that turns \"####\" into \"###\" makes every dialog a tab.
    Only done when both texts have the same number of headings (then the n-th heading is the n-th heading)."""
    levels = [len(m.group(1)) for m in re.finditer(r"(?m)^\s*(#+)\s", source)]
    if len(levels) != _headings(text):
        return text
    it = iter(levels)
    return re.sub(r"(?m)^(\s*)#+(\s)", lambda m: f"{m.group(1)}{'#' * next(it)}{m.group(2)}", text)


def _try(ask, cut, system: str, chunk: str, non_latin: bool, deadline: float, temperatures=(0.1, 0.3)) -> str:
    for temperature in temperatures:
        if time.monotonic() > deadline - 20:
            logger.warning("[AI-TRANSLATE] no time left for: %.60s", chunk.strip().replace("\n", " "))
            return ""
        text = ask(system, chunk, temperature)
        why = rejection(chunk, text, cut(), non_latin)
        if not why:
            return clean_headings(restore_levels(chunk, text.strip())) if non_latin else restore_levels(chunk, text.strip())
        logger.info("[AI-TRANSLATE] rejected (%s) at temperature %s: %.60s", why, temperature, chunk.strip().replace("\n", " "))
    return ""


def translate_markdown(ask, cut, markdown: str, language: str, deadline: float, progress=None, non_latin: bool = False,
                       stats: dict | None = None) -> str:
    """The whole text in `language`. A chunk that fails is translated again in smaller pieces; a piece that still fails (or
    does not fit the time) stays English. `stats`, when given, receives {"chunks": n, "kept_english": pieces left in English}."""
    system, chunks, parts, kept = _TRANSLATE.format(language=language), split_chunks(markdown), [], 0
    started = time.monotonic()
    for n, chunk in enumerate(chunks, 1):
        if progress:
            progress(n, len(chunks), language, started)
        done = _try(ask, cut, system, chunk, non_latin, deadline, temperatures=(0.1,))
        if not done:
            pieces, translated = split_chunks(chunk, PIECE_CHARS) if len(chunk) > PIECE_CHARS else [chunk], []
            for piece in pieces:
                got = _try(ask, cut, system, piece, non_latin, deadline)
                kept += 0 if got else 1
                translated.append(got or piece.strip())
            done = "\n\n".join(translated)
        parts.append(done)
    if stats is not None:
        stats.update(chunks=len(chunks), kept_english=kept)
    if kept:   # visible in the server log: the guide is complete but part of it is still English
        logger.warning("[AI-TRANSLATE] %s: %d piece(s) of %d chunk(s) stayed English (rejected twice or out of time)", language, kept, len(chunks))
    return "\n\n".join(parts)
