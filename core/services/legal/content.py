"""Resolve the Privacy / Terms text: DB version first, i18n defaults as fallback."""

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from core.authentication.legal import LEGAL_VERSION

LANGS = ("en", "ar", "fr", "de")
DOCS = {
    "terms": {"prefix": "terms", "sections": 9, "title_key": "legal_terms_title"},
    "privacy": {"prefix": "privacy", "sections": 8, "title_key": "legal_privacy_title"},
}


@lru_cache(maxsize=8)
def _i18n(lang: str) -> dict:
    path = Path(settings.BASE_DIR) / "static" / "i18n" / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def default_document(lang: str, doc: str) -> dict:
    """The built-in text (i18n keys) of one document in one language."""
    spec = DOCS[doc]
    texts = _i18n(lang)
    en = _i18n("en")
    prefix = spec["prefix"]
    sections = []
    for i in range(1, spec["sections"] + 1):
        tk, bk = f"{prefix}_s{i}_title", f"{prefix}_s{i}_body"
        sections.append({"title": texts.get(tk) or en.get(tk, ""), "body": texts.get(bk) or en.get(bk, "")})
    return {"title": texts.get(spec["title_key"]) or en.get(spec["title_key"], ""), "sections": sections}


def _latest():
    from core.models import LegalVersion

    return LegalVersion.objects.order_by("-created_at", "-id").first()


@lru_cache(maxsize=1)
def _current_snapshot() -> tuple:
    row = _latest()
    if row is None:
        return (LEGAL_VERSION, False, None, {})
    return (row.label, row.require_reconsent, row.pk, row.content or {})


def clear_cache() -> None:
    _current_snapshot.cache_clear()


def current_label() -> str:
    return _current_snapshot()[0]


def current_requires_reconsent() -> bool:
    return _current_snapshot()[1]


def current_version_id():
    return _current_snapshot()[2]


def _clean_sections(raw) -> list:
    out = []
    for item in raw or []:
        if isinstance(item, dict) and (str(item.get("title", "")).strip() or str(item.get("body", "")).strip()):
            out.append({"title": str(item.get("title", "")), "body": str(item.get("body", ""))})
    return out


def override_document(content: dict, lang: str, doc: str):
    """The stored override for (lang, doc), or None when empty (use defaults)."""
    node = ((content or {}).get(lang) or {}).get(doc) or {}
    sections = _clean_sections(node.get("sections"))
    title = str(node.get("title", "")).strip()
    if not sections:
        return None
    return {"title": title, "sections": sections}


def get_document(lang: str, doc: str) -> dict:
    """Document for rendering: {"title", "sections", "overridden"}."""
    lang = lang if lang in LANGS else "en"
    custom = override_document(_current_snapshot()[3], lang, doc)
    if custom is None:
        base = default_document(lang, doc)
        base["overridden"] = False
        return base
    default_title = default_document(lang, doc)["title"]
    return {"title": custom["title"] or default_title, "sections": custom["sections"], "overridden": True}


def get_editor_payload() -> dict:
    """Defaults plus the current stored content for every language/doc."""
    snapshot = _current_snapshot()
    current = {}
    defaults = {}
    for lang in LANGS:
        current[lang] = {}
        defaults[lang] = {}
        for doc in DOCS:
            defaults[lang][doc] = default_document(lang, doc)
            custom = override_document(snapshot[3], lang, doc)
            current[lang][doc] = custom or defaults[lang][doc]
    return {"current_label": snapshot[0], "current_version_id": snapshot[2], "current": current, "defaults": defaults}
