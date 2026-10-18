"""Language of a finished document, from how DENSE the French / German evidence words are (not from "one word is enough").

The router's detect() treats one real French word as proof, which is right for a short question and wrong for a long
English guide: a few words such as "documentation" or "plans" are enough to tag 4,000 words of English as French and put a
French "Généré le" line in an English file. A real French or German text is full of such words, an English one is not."""

from __future__ import annotations

import re

from ..query_engine.lexicon import language
from ..query_engine.lexicon_fr_de import LANGS, _evidence, fold

MIN_DENSITY = 0.08   # share of the words that belong to the language's own evidence list
_WORD = re.compile(r"[a-z]+")


def document_language(content: str) -> str:
    """'ar' | 'fr' | 'de' | 'en' for a whole document."""
    if language(content[:2000]) == "ar" or language(content) == "ar":
        return "ar"
    words = _WORD.findall(fold(str(content or "").lower()))
    if len(words) < 8:
        return language(content)
    best, density = "en", 0.0
    for code in LANGS:
        domain, possessive, function = _evidence(code)
        own = domain | possessive | function
        share = sum(1 for w in words if w in own) / len(words)
        if share > density:
            best, density = code, share
    return best if density >= MIN_DENSITY else "en"
