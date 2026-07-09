from django.db import models

class AppSettings(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.key

    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value):
        obj, _ = cls.objects.update_or_create(key=key, defaults={"value": value})
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
