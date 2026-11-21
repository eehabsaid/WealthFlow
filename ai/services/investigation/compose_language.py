"""Which language a requested document must be written in.

Decided from the request itself first, and the model only as the last resort, because a one-word model answer is fragile: a reply
such as "Arabic (MSA)", an empty reply or a refused call used to mean "no language named" and the whole guide silently came back
in English (a user who asked for a guide "in well formatted Arabic" got English headings and English chapters).

  1. the request names a language ("in Arabic", "بالعربية", "en français", "auf Deutsch")  -> that language
  2. it names none and is itself written in Arabic / French / German                         -> the language of the request
  3. otherwise the model names it in one word (asked twice, parsed leniently) and, when it is not the request's own language,
     a second YES/NO question confirms that the request really asks for it.
"""

from __future__ import annotations

import re

from ai.services.protocol import log_reply, parse_yes_no
from ai.services.query_engine.lexicon import language, norm
from ai.services.query_engine.lexicon_fr_de import fold

# canonical English name -> the names a request may use for it (normalised: lowercase, accents folded, Arabic alef / ya / ta-marbuta folded)
NAMES = {
    "English": ("english", "anglais", "englisch", "ingles", "انجليزي", "انجليزيه", "انكليزي", "انكليزيه"),
    "Arabic": ("arabic", "arabe", "arabisch", "arabo", "عربي", "عربيه"),
    "French": ("french", "francais", "franzosisch", "frances", "فرنسي", "فرنسيه"),
    "German": ("german", "deutsch", "allemand", "aleman", "الماني", "المانيه"),
    "Spanish": ("spanish", "espanol", "espagnol", "spanisch", "اسباني", "اسبانيه"),
    "Italian": ("italian", "italiano", "italien", "italienisch", "ايطالي", "ايطاليه"),
    "Turkish": ("turkish", "turkce", "turc", "turkisch", "تركي", "تركيه"),
    "Russian": ("russian", "russe", "russisch", "روسي", "روسيه"),
}
CODES = {"ar": "Arabic", "fr": "French", "de": "German"}
NON_LATIN = ("Arabic", "Russian")
_AR = r"\u0600-\u06ff"
_ARABIC_FORM = {name: re.compile(rf"(?<![{_AR}])(?:وبال|وال|بال|لل|ال|ب|ل|و)?(?:{'|'.join(w for w in words if not w.isascii())})[هة]?(?![{_AR}])")
                for name, words in NAMES.items()}
_LATIN_FORM = {name: re.compile(rf"(?<![a-z])(?:{'|'.join(w for w in words if w.isascii())})(?![a-z])") for name, words in NAMES.items()}
_LANGUAGE_Q = ("Answer with one word only: the language the requested document must be written in. Use the language the request "
               "names; if it names none, the language the request itself is written in. Reply with the language's English name "
               "(for example English, Arabic, French) and nothing else.")
_NAMED_Q = ("Answer YES or NO only. Does the request below explicitly ask for the document to be written in {language}? Answer NO when "
            "the request only happens to be written in another language or names no language at all.")
_LATIN_Q = "Answer YES or NO only. Is {language} normally written in the Latin alphabet (like English, French or German)?"
_WORD = re.compile(r"[^\W\d_]+")


def named_languages(text: str) -> list[str]:
    """The languages a request names, in the order they are named (canonical English names, each once)."""
    folded = norm(fold(str(text or "")))
    found = sorted(((m.start(), name) for name in NAMES for form in (_ARABIC_FORM[name], _LATIN_FORM[name]) for m in form.finditer(folded)))
    return list(dict.fromkeys(name for _, name in found))


def canonical(word: str) -> str:
    """The canonical name of a language word in any of the supported spellings ("العربية", "français"), else the word itself."""
    found = named_languages(word)
    return found[0] if found else word.strip()


def _one_word(reply: str) -> str:
    """The language a model reply names: the reply itself when it is one short alphabetic phrase, else the first language it mentions
    ("Arabic (Modern Standard Arabic)", "**Arabic**.", "The language is Arabic"); "" when it names none."""
    text = str(reply or "").strip().strip(".\"'`*").split("\n")[0].strip()
    if text and len(text) <= 24 and all(ch.isalpha() or ch in " -" for ch in text):
        return canonical(text)
    named = named_languages(" ".join(_WORD.findall(str(reply or ""))[:12]))
    return named[0] if named else ""


def _outcome(name: str) -> str:
    return "" if not name or name == "English" or name.lower().startswith("english") else name


def target_language(ask, user_text: str) -> str:
    """The language the document must be in, or "" for English / when nothing names another language."""
    named = named_languages(user_text)
    if len(named) == 1:
        return _outcome(named[0])
    own = CODES.get(language(user_text), "") if not named else ""
    if own:
        return own    # a request written in Arabic / French / German that names no language: the answer is in the request's language
    word = _one_word(ask(_LANGUAGE_Q, user_text, 0)) or _one_word(ask(_LANGUAGE_Q, user_text, 0.3))   # an empty reply is asked once more
    if not word:
        return next((n for n in named if _outcome(n)), "")
    if not _outcome(word):
        return ""
    if word in named:
        return word
    raw = ask(_NAMED_Q.format(language=word), user_text, 0)   # a one-word answer can be wrong (an English request came back as Arabic): confirmed once
    answer = parse_yes_no(raw)
    log_reply("language_named", raw, answer)
    return word if answer is not False else ""


def uses_latin_script(ask, language_name: str) -> bool:
    """Known languages are decided here; any other language is asked (a model answer, YES / NO)."""
    if language_name in NAMES:
        return language_name not in NON_LATIN
    return ask(_LATIN_Q.format(language=language_name), language_name, 0).strip().upper().startswith("YES")
