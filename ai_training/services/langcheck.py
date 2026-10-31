"""Which language an answer is written in, with no word lists of our own.

Writing system tells Arabic from Latin text (textutil.script_of). Among Latin-script languages the evidence is the app's own
translation files: words that appear in one language's file and in neither of the other two are that language's evidence.
An answer is "confirmed" in a language only when that language has at least MIN_HITS evidence words and clearly more than the
runner-up; anything weaker is "unconfirmed" (the callers decide what unconfirmed means)."""

from __future__ import annotations

import re
from functools import lru_cache

from . import phrasing
from .textutil import script_of

LATIN = ("en", "fr", "de")
MIN_HITS = 2
_WORD = re.compile(r"[^\W\d_]{3,}", re.U)


def _words(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(str(text or ""))}


@lru_cache(maxsize=1)
def _evidence() -> dict[str, frozenset]:
    """Only strings that are really translated count: a French or German file still holds untranslated English text, which would make
    English words look French or German."""
    en = phrasing.catalog("en")
    pools = {"en": set()}
    for lang in ("fr", "de"):
        cat = phrasing.catalog(lang)
        keys = [k for k, v in cat.items() if k in en and v != en[k]]
        pools[lang] = set().union(*(_words(cat[k]) for k in keys)) if keys else set()
        pools["en"] |= set().union(*(_words(en[k]) for k in keys)) if keys else set()
    return {lang: frozenset(pools[lang] - set().union(*(pools[o] for o in LATIN if o != lang))) for lang in LATIN}


def detect(text: str) -> str:
    """"ar" for Arabic script, "en" / "fr" / "de" when confirmed by evidence words, "" when it cannot be confirmed."""
    script = script_of(text)
    if script == "ARABIC":
        return "ar"
    if script not in ("LATIN", ""):
        return ""
    words, evidence = _words(text), _evidence()
    hits = sorted(((len(words & evidence[lang]), lang) for lang in LATIN), reverse=True)
    best, second = hits[0], hits[1]
    return best[1] if best[0] >= MIN_HITS and best[0] >= 2 * max(second[0], 1) - 1 and best[0] > second[0] else ""


def verdict(question: str, answer: str, declared: str = "") -> str:
    """"same" | "other" | "unconfirmed" for the answer's language against the question's (declared tag, else detected)."""
    want = declared or detect(question) or ("ar" if script_of(question) == "ARABIC" else "")
    if script_of(answer) != script_of(question) and script_of(answer) and script_of(question):
        return "other"
    got = detect(answer)
    if got and want and got != want:
        return "other"
    if got and got == want:
        return "same"
    return "unconfirmed"
