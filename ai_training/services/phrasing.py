"""Wording. Sentence frames (several per intent and language) live in frames_en/ar/fr/de.py; every NOUN comes from the live app:
table and field names are translated with the app's own i18n files (static/i18n/<lang>.json) by matching the English text, so a
label the app has no translation for simply produces no question in that language (when in doubt, throw it out)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from core.services.ai.query_engine.labels import month_label

from . import frames_ar, frames_de, frames_en, frames_fr

LANGS = ("en", "ar", "fr", "de")
FRAMES = {"en": frames_en.F, "ar": frames_ar.F, "fr": frames_fr.F, "de": frames_de.F}


@lru_cache(maxsize=8)
def catalog(lang: str) -> dict:
    try:
        with open(Path(settings.BASE_DIR) / "static" / "i18n" / f"{lang}.json", encoding="utf-8") as fh:
            return {str(k): str(v).strip() for k, v in json.load(fh).items() if isinstance(v, str)}
    except (OSError, ValueError):
        return {}


@lru_cache(maxsize=512)
def translate(text_en: str, lang: str) -> str | None:
    """The app's own translation of an English UI word (singular or plural); the most common one when several keys agree."""
    want = str(text_en or "").strip().lower()
    if lang == "en":
        return want.title() if want else None
    en, target = catalog("en"), catalog(lang)
    found = [target[k] for k, v in en.items() if v.lower() in (want, want + "s", want + "es") and target.get(k) and "{" not in target[k]]
    return max(set(found), key=found.count) if found else None


def concept(key: str, lang: str) -> str | None:
    """A UI text by its key (e.g. "nav_expenses", "net_worth") in the language; None when the app lacks it."""
    value = catalog(lang).get(key)
    return value if value and "{" not in value else None


def table_label(model, lang: str) -> str | None:
    if lang == "en":
        return f"{model._meta.verbose_name} records"
    return translate(str(model._meta.verbose_name), lang) or translate(str(model._meta.verbose_name_plural), lang)


def field_label(field, lang: str) -> str | None:
    return str(field.verbose_name) if lang == "en" else translate(str(field.verbose_name), lang)


def month(lang: str, year: int, mon: int) -> str:
    return month_label(lang, year, mon)


def variants(intent: str, lang: str) -> int:
    return len(FRAMES[lang].get(intent, ()))


def say(intent: str, lang: str, variant: int = 0, **slots) -> str | None:
    """The question text, or None when this language has no frame for the intent or a slot is empty (a missing label)."""
    frames = FRAMES[lang].get(intent)
    if not frames or any(v is None or v == "" for v in slots.values()):
        return None
    return frames[variant % len(frames)].format(**slots)
