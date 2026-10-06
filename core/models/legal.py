"""Editable Privacy Policy / Terms of Service text, one row per published version.

The text of every language lives in `content` as
`{lang: {doc: {"title": str, "sections": [{"title": str, "body": str}]}}}`
with doc in ("terms", "privacy"). Anything missing or blank falls back to the
i18n defaults (static/i18n/<lang>.json legal_* keys), so an empty table means
"use the built-in text". The newest row is the current version; older rows are
the history. Accounts keep the `terms_version` label they accepted at signup
(UserProfile.terms_version) regardless of later versions.
"""

from django.contrib.auth.models import User
from django.db import models


class LegalVersion(models.Model):
    label = models.CharField(max_length=40, unique=True)
    content = models.JSONField(default=dict, blank=True)
    require_reconsent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="legal_versions"
    )

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.label

    def to_dict(self, include_content=False):
        data = {
            "id": self.pk,
            "label": self.label,
            "require_reconsent": self.require_reconsent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by.username if self.created_by else "",
        }
        if include_content:
            data["content"] = self.content or {}
        return data
