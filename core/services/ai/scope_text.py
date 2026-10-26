"""The user-facing refusal for a question outside the chat domain, read from the app's own i18n files (static/i18n/<lang>.json) so
the wording and the domain names are exactly what the UI shows, in the user's language."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from .domains import APP, BUSINESS, enabled_domains

LANGS = ("en", "ar", "fr", "de")
MIN_ARABIC_LETTERS = 4
_DOMAIN_KEY = {BUSINESS: "ai_domain_business_data", APP: "ai_domain_app_features"}


@lru_cache(maxsize=8)
def _locale(lang: str) -> dict:
    path = Path(settings.BASE_DIR) / "static" / "i18n" / f"{lang if lang in LANGS else 'en'}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def text(lang: str, key: str) -> str:
    return str(_locale(lang).get(key) or _locale("en").get(key) or "")


def reply_language(question: str) -> str:
    """The language of the answer: query_engine's detector, except that a request mixing a few Arabic words with Latin terms (\"HTML\",
    \"PDF\", product names) is still an Arabic request, not an English one."""
    from core.services.ai.query_engine.lexicon import language

    lang = language(question)
    letters = [c for c in str(question or "") if c.isalpha()]
    arabic = sum(1 for c in letters if "\u0600" <= c <= "\u06ff")
    return "ar" if lang == "en" and arabic >= MIN_ARABIC_LETTERS and arabic >= 0.1 * len(letters) else lang


def refusal(lang: str, domain: str = "") -> str:
    """No-information answer; with a known domain it says what that domain covers and which domain to switch to."""
    if domain not in _DOMAIN_KEY:
        return text(lang, "ai_scope_no_info")
    other = APP if domain == BUSINESS else BUSINESS
    kind = "refused_business" if domain == BUSINESS else "refused_app"
    if other not in enabled_domains():
        kind = "refused_locked"
    template = text(lang, f"ai_scope_{kind}")
    return template.format(current=text(lang, _DOMAIN_KEY[domain]), other=text(lang, _DOMAIN_KEY[other]))


def all_refusals() -> set[str]:
    """Every refusal wording (all languages, domains and enabled-state variants): to recognise a saved refusal and never attach a file."""
    out = {text(lang, "ai_scope_no_info") for lang in LANGS}
    for lang in LANGS:
        for domain in _DOMAIN_KEY:
            other = APP if domain == BUSINESS else BUSINESS
            for kind in ("refused_business" if domain == BUSINESS else "refused_app", "refused_locked"):
                out.add(text(lang, f"ai_scope_{kind}").format(current=text(lang, _DOMAIN_KEY[domain]), other=text(lang, _DOMAIN_KEY[other])))
    return out
