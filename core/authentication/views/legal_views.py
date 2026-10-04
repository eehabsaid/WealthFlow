"""Public Privacy Policy and Terms of Service pages.

The text lives in the i18n files (legal_privacy_* / legal_terms_* keys) so it is
translated in en/ar/fr/de like the rest of the UI. The page is rendered
server-side in English (readable without JavaScript) and the shared auth
language loader swaps in the visitor's language.
"""

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.views.decorators.http import require_GET

from core.authentication.legal import LEGAL_VERSION
from core.authentication.views.helpers import _render_auth

PRIVACY_SECTIONS = 8
TERMS_SECTIONS = 9


@lru_cache(maxsize=1)
def _en_texts() -> dict:
    path = Path(settings.BASE_DIR) / "static" / "i18n" / "en.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _sections(prefix: str, count: int) -> list:
    texts = _en_texts()
    return [
        {
            "title_key": f"{prefix}_s{i}_title",
            "title": texts.get(f"{prefix}_s{i}_title", ""),
            "body_key": f"{prefix}_s{i}_body",
            "body": texts.get(f"{prefix}_s{i}_body", ""),
        }
        for i in range(1, count + 1)
    ]


def _legal_page(request, template, prefix, count, title_key):
    texts = _en_texts()
    return _render_auth(
        request,
        template,
        {
            "sections": _sections(prefix, count),
            "title_key": title_key,
            "title": texts.get(title_key, ""),
            "legal_version": LEGAL_VERSION,
            "draft_notice": texts.get("legal_draft_notice", ""),
        },
    )


@require_GET
def privacy_view(request):
    return _legal_page(request, "legal/privacy.html", "privacy", PRIVACY_SECTIONS, "legal_privacy_title")


@require_GET
def terms_view(request):
    return _legal_page(request, "legal/terms.html", "terms", TERMS_SECTIONS, "legal_terms_title")
