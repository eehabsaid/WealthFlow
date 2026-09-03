"""
ContentType label <-> ContentType resolution helpers used by backup export
and restore.
"""

from __future__ import annotations

from django.contrib.contenttypes.models import ContentType


def resolve_content_type(label: str | None) -> ContentType | None:
    if not label:
        return None
    try:
        app_label, model_name = label.split(".", 1)
        return ContentType.objects.get(app_label=app_label, model=model_name)
    except (ValueError, ContentType.DoesNotExist):
        return None


def content_type_label(ct: ContentType | None) -> str | None:
    if ct is None:
        return None
    return f"{ct.app_label}.{ct.model}"
