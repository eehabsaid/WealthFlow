from django.db import models
from django.contrib.auth.models import User
from datetime import date, datetime


def _date_to_iso(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value:
        return str(value)
    return ""


class AIConversation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255, default="New Conversation", blank=True)
    is_deleted = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "is_deleted": self.is_deleted,
            "is_pinned": self.is_pinned,
            "created_at": _date_to_iso(self.created_at),
            "updated_at": _date_to_iso(self.updated_at),
            "messages_count": self.messages.filter(is_deleted=False).count(),
        }
