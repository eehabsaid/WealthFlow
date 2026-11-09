"""
ContentType label <-> ContentType resolution helpers used by backup export
and restore.
"""

from __future__ import annotations

from django.contrib.contenttypes.models import ContentType


# Backups made before the AI models moved to app "ai" label them "core.<model>".
LEGACY_AI_MODELS = frozenset({
    "aiknowledgeentry", "aipromptcategory", "aiconversation", "aimemorynote", "aimessage",
    "aichatblock", "aiattachment", "aiprompt", "aianswerfeedback",
})


def current_app_label(app_label: str, model_name: str) -> str:
    """Map an old backup's app label to today's (core -> ai for the 9 AI models)."""
    return "ai" if app_label == "core" and model_name in LEGACY_AI_MODELS else app_label


def resolve_content_type(label: str | None) -> ContentType | None:
    if not label:
        return None
    try:
        app_label, model_name = label.split(".", 1)
        return ContentType.objects.get(app_label=current_app_label(app_label, model_name), model=model_name)
    except (ValueError, ContentType.DoesNotExist):
        return None


def content_type_label(ct: ContentType | None) -> str | None:
    if ct is None:
        return None
    return f"{ct.app_label}.{ct.model}"
