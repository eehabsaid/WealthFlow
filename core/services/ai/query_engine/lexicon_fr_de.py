"""French / German understanding for the router: fold, detect, and rewrite a question into the canonical English
tokens the capability regexes already key on (months, relative periods, domain nouns, metric / analytic / action words).

Deterministic, no LLM, no extra calls. The rewrite only steers routing: category and bank names are matched against the
accent-folded ORIGINAL text as well (see slots.route), answers are rendered from fr/de label tables (labels_fr/de.py),
and anything the rules do not understand simply stays untouched and falls through like any unrecognised question.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from . import lexicon_de, lexicon_fr

_SPECIAL = str.maketrans({"ß": "ss", "œ": "oe", "æ": "ae", "’": "'", "‘": "'", "`": "'"})
_WORD = re.compile(r"[a-z]+")
_SPACES = re.compile(r"\s+")
LANGS = {"fr": lexicon_fr, "de": lexicon_de}


def fold(text: str) -> str:
    """Strip Latin accents/umlauts (é->e, ü->u, ß->ss) but leave every other script (Arabic) untouched."""
    out: list[str] = []
    for ch in unicodedata.normalize("NFKD", str(text or "").translate(_SPECIAL)):
        if unicodedata.combining(ch) and out and out[-1].isascii() and out[-1].isalpha():
            continue
        out.append(ch)
    return "".join(out)


@lru_cache(maxsize=4)
def _evidence(lang: str) -> tuple[frozenset, frozenset, frozenset]:
    """(domain words, possessives, function words). Domain words = the hand-picked list + every rewrite-table word that
    is not also an English word, so the detector cannot drift away from what the rules actually understand."""
    mod = LANGS[lang]
    derived = {k for k, v in mod.WORDS.items() if k != v and len(k) >= 4 and k not in mod.ENGLISH_CLASH}
    return frozenset(mod.DOMAIN_WORDS | mod.EXTRA_DOMAIN | derived), frozenset(mod.POSSESSIVES), frozenset(mod.FUNCTION_WORDS)


def detect(text: str) -> str | None:
    """'fr' | 'de' | None. Domain words and possessives weigh 2, other function words 1, threshold 2: one real word of the
    language is enough ("Mon or", "Meine Zertifikate"), while English, which shares a few short words with both, is never
    reclassified (guarded by a test over the whole English corpus)."""
    low = fold(str(text or "").lower())
    if not low or any("\u0600" <= c <= "\u06ff" for c in low):
        return None
    words = set(_WORD.findall(low))
    best, best_score = None, 0
    for code in LANGS:
        domain, possessive, function = _evidence(code)
        score = 2 * len(words & (domain | possessive)) + len(words & (function - domain - possessive))
        if score > best_score:
            best, best_score = code, score
    return best if best_score >= 2 else None


@lru_cache(maxsize=4)
def _compiled(lang: str):
    mod = LANGS[lang]
    phrases = [(re.compile(p), r) for p, r in mod.PHRASES]
    words = mod.WORDS
    alt = "|".join(sorted(map(re.escape, words), key=len, reverse=True))
    return phrases, words, re.compile(rf"(?<![a-z])({alt})(?![a-z])")


def to_english(q: str, lang: str) -> str:
    """Rewrite a normalised question (lowercase) into canonical English routing tokens. Unknown words are kept."""
    if lang not in LANGS:
        return q
    phrases, words, word_rx = _compiled(lang)
    text = " " + fold(q) + " "
    for rx, repl in phrases:
        text = _SPACES.sub(" ", rx.sub(repl, text))   # collapse after every rule: later patterns expect single spaces
    text = word_rx.sub(lambda m: words[m.group(1)], text)
    return re.sub(r"\s+", " ", text).strip()
