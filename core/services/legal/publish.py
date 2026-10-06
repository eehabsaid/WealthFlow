"""Validate and publish a new legal-text version (sysadmin editor)."""

import re

from django.db import IntegrityError, transaction

from core.models import LegalVersion, UserProfile
from core.services.legal.content import DOCS, LANGS, clear_cache, default_document

LABEL_RE = re.compile(r"^[\w.\-]{1,40}$")
MAX_SECTIONS = 40
MAX_TITLE = 200
MAX_BODY = 8000


class LegalPublishError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _normalise(content) -> dict:
    """Keep only known languages/docs; drop a doc that equals the built-in text."""
    if not isinstance(content, dict):
        raise LegalPublishError("invalid_content")
    clean: dict = {}
    for lang in LANGS:
        for doc in DOCS:
            node = ((content.get(lang) or {}).get(doc)) or {}
            sections = []
            for item in node.get("sections") or []:
                if not isinstance(item, dict):
                    raise LegalPublishError("invalid_content")
                title, body = str(item.get("title", "")).strip(), str(item.get("body", "")).strip()
                if not title and not body:
                    continue
                if len(title) > MAX_TITLE or len(body) > MAX_BODY:
                    raise LegalPublishError("too_long")
                sections.append({"title": title, "body": body})
            if len(sections) > MAX_SECTIONS:
                raise LegalPublishError("too_many_sections")
            title = str(node.get("title", "")).strip()
            if len(title) > MAX_TITLE:
                raise LegalPublishError("too_long")
            default = default_document(lang, doc)
            same = sections == [
                {"title": s["title"].strip(), "body": s["body"].strip()} for s in default["sections"]
            ]
            if not sections or (same and title in ("", default["title"])):
                continue
            clean.setdefault(lang, {})[doc] = {"title": title, "sections": sections}
    return clean


@transaction.atomic
def publish_version(*, label: str, content, require_reconsent: bool, user) -> LegalVersion:
    label = (label or "").strip()
    if not LABEL_RE.match(label):
        raise LegalPublishError("invalid_label")
    cleaned = _normalise(content)
    try:
        row = LegalVersion.objects.create(
            label=label, content=cleaned, require_reconsent=bool(require_reconsent), created_by=user
        )
    except IntegrityError as exc:
        raise LegalPublishError("duplicate_label") from exc
    clear_cache()
    _accept_for_publisher(user, row)
    return row


def _accept_for_publisher(user, row) -> None:
    """The sysadmin who publishes a version wrote it, so they are not asked to re-accept it."""
    from django.utils import timezone

    profile = UserProfile.objects.filter(user=user).first() if user else None
    if profile is not None:
        profile.terms_version = row.label
        profile.terms_accepted_at = timezone.now()
        profile.save(update_fields=["terms_version", "terms_accepted_at"])
