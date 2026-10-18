from django.db import models
from datetime import date, datetime


def _date_to_iso(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value:
        return str(value)
    return ""


class AIKnowledgeEntry(models.Model):
    """
    Distilled, verified long-term domain knowledge entry.
    Stores business rules, codebase architecture, user preferences, and app evolution facts.
    """
    CATEGORY_CHOICES = [
        ("business_rule", "Business Rule & Calculation"),
        ("codebase_architecture", "Codebase Architecture & Services"),
        ("user_preference", "User Directive & Preference"),
        ("app_evolution", "Application Evolution & Feature"),
    ]

    key = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="business_rule")
    title = models.CharField(max_length=255)
    content = models.TextField()
    confidence = models.FloatField(default=1.0)
    source = models.CharField(max_length=100, default="autonomous_learning")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "confidence": self.confidence,
            "source": self.source,
            "is_active": self.is_active,
            "created_at": _date_to_iso(self.created_at),
            "updated_at": _date_to_iso(self.updated_at),
        }
