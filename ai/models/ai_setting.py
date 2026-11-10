"""AISetting: the AI app's own key/value settings (global row owner=NULL, optional per-user rows)."""
from django.conf import settings
from django.db import models

from ai.constants import AI_USER_SETTING_KEYS, USE_GENERAL_KEY


class AISetting(models.Model):
    key = models.CharField(max_length=100)
    value = models.TextField()
    description = models.CharField(max_length=300, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
                              related_name="ai_settings")

    class Meta:
        unique_together = ["key", "owner"]

    def __str__(self):
        return self.key if self.owner_id is None else f"{self.key} ({self.owner_id})"

    @classmethod
    def get(cls, key, default=None, user=None):
        if user is not None and getattr(user, "is_authenticated", False) and not cls._on_general_ai(key, user):
            row = cls.objects.filter(key=key, owner=user).first()
            if row is not None:
                return row.value
        row = cls.objects.filter(key=key, owner=None).first()
        return row.value if row is not None else default

    @classmethod
    def _on_general_ai(cls, key, user):
        """True when `key` is a per-user AI key and the user runs on the general settings (the default)."""
        if key not in AI_USER_SETTING_KEYS:
            return False
        flag = cls.objects.filter(key=USE_GENERAL_KEY, owner=user).values_list("value", flat=True).first()
        return str(flag if flag is not None else "true").strip().lower() not in ("false", "0", "no")

    @classmethod
    def set(cls, key, value, user=None):
        owner = user if (user is not None and getattr(user, "is_authenticated", False)) else None
        obj, _ = cls.objects.update_or_create(key=key, owner=owner, defaults={"value": value})
        return obj
