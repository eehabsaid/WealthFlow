from django.contrib.auth.models import User
from django.db import models


class AIMemoryNote(models.Model):
    """One free-text reminder the AI wrote for itself from past chats (goals, results with numbers and dates,
    decisions, preferences). Per user, never shared. Notes are reminders, not facts: live data overrides them."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_memory_notes")
    title = models.CharField(max_length=120)
    body = models.TextField()
    always = models.BooleanField(default=False)   # a standing instruction/preference: shown in full in every chat, not just indexed
    source_conversation = models.ForeignKey(
        "AIConversation", on_delete=models.SET_NULL, null=True, blank=True, related_name="memory_notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "always": self.always,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
            "conversation_id": self.source_conversation_id,
        }
