from django.db import models
from django.conf import settings


class AppSettings(models.Model):
    """Platform-wide OR per-user key/value settings, depending on the key.

    A row with owner=NULL is the global/platform default (and, for the
    catalog-style settings, also the template new users are seeded from
    — see the 00xx_per_user_settings migration). Passing `user=` to
    get()/set() looks up (key, owner=user) first, falling back to the
    global row. Callers that never pass `user=` get the pre-existing
    global-only behavior unchanged.
    """

    key = models.CharField(max_length=100)
    value = models.TextField()
    description = models.CharField(max_length=300, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="app_settings",
    )

    class Meta:
        unique_together = ["key", "owner"]

    def __str__(self):
        return self.key if self.owner_id is None else f"{self.key} ({self.owner_id})"

    @classmethod
    def get(cls, key, default=None, user=None):
        if user is not None and getattr(user, "is_authenticated", False):
            try:
                return cls.objects.get(key=key, owner=user).value
            except cls.DoesNotExist:
                pass
        try:
            return cls.objects.get(key=key, owner=None).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value, user=None):
        owner = user if (user is not None and getattr(user, "is_authenticated", False)) else None
        obj, _ = cls.objects.update_or_create(
            key=key, owner=owner, defaults={"value": value}
        )
        return obj


class EmailTemplate(models.Model):
    key = models.CharField(max_length=100, unique=True)
    subject_translations = models.JSONField(default=dict, blank=True)
    body_translations = models.JSONField(default=dict, blank=True)
    description_translations = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def get_subject(self, lang="en"):
        return (self.subject_translations or {}).get(lang) or (self.subject_translations or {}).get("en", "")

    def get_body(self, lang="en"):
        return (self.body_translations or {}).get(lang) or (self.body_translations or {}).get("en", "")

    def get_description(self, lang="en"):
        return (self.description_translations or {}).get(lang) or (self.description_translations or {}).get("en", "")

    def to_dict(self, lang="en"):
        return {
            "id": self.id,
            "key": self.key,
            "subject": self.get_subject(lang),
            "body": self.get_body(lang),
            "description": self.get_description(lang),
            "subject_translations": self.subject_translations or {},
            "body_translations": self.body_translations or {},
            "description_translations": self.description_translations or {},
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }

    def __str__(self):
        return self.key
