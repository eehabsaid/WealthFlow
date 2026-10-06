"""Public Privacy Policy and Terms of Service pages.

The text comes from core.services.legal: the newest LegalVersion row edited by
a sysadmin (Settings > Legal Text), falling back per language/document to the
i18n files (legal_privacy_* / legal_terms_* keys). The page is rendered
server-side in the visitor's language, readable without JavaScript. Built-in
text keeps its data-i18n keys so the shared auth language switcher can swap it;
edited text has none (legal_lang.js reloads the page on a language change).
"""

from django.utils.safestring import mark_safe
from django.views.decorators.http import require_GET

from core.authentication.views.helpers import _render_auth, _request_lang
from core.services.legal import DOCS, current_label, get_document
from core.services.legal.content import _i18n


# Section counts of the built-in text (kept for the i18n coverage tests).
PRIVACY_SECTIONS = DOCS["privacy"]["sections"]
TERMS_SECTIONS = DOCS["terms"]["sections"]


def _i18n_attr(key: str):
    """`data-i18n="key"` for built-in text; nothing for edited text (it has no i18n key). The key is
    one of our own legal_* constants, never user input, so marking it safe is fine."""
    return mark_safe(f'data-i18n="{key}"') if key else ""


def _legal_page(request, template, doc):
    lang = _request_lang(request)
    spec = DOCS[doc]
    page = get_document(lang, doc)
    overridden = page["overridden"]
    prefix = spec["prefix"]
    sections = [
        {
            "title_attr": _i18n_attr("" if overridden else f"{prefix}_s{i}_title"),
            "title": s["title"],
            "body_attr": _i18n_attr("" if overridden else f"{prefix}_s{i}_body"),
            "body": s["body"],
        }
        for i, s in enumerate(page["sections"], start=1)
    ]
    return _render_auth(
        request,
        template,
        {
            "sections": sections,
            "overridden": overridden,
            "title_attr": _i18n_attr("" if overridden else spec["title_key"]),
            "title": page["title"],
            "legal_version": current_label(),
            "draft_notice": _i18n(lang if lang in ("en", "ar", "fr", "de") else "en").get("legal_draft_notice", ""),
        },
    )


@require_GET
def privacy_view(request):
    return _legal_page(request, "legal/privacy.html", "privacy")


@require_GET
def terms_view(request):
    return _legal_page(request, "legal/terms.html", "terms")
