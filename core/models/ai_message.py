from django.db import models
from django.utils import timezone
from datetime import date, datetime
from .ai_conversation import AIConversation


def _date_to_iso(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value:
        return str(value)
    return ""


class AIMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    tool_calls = models.JSONField(default=list, blank=True)
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.role in ("user", "assistant"):
            # A new message moves its chat to the top of the sidebar (queryset update: no extra save signal, no recursion)
            AIConversation.objects.filter(pk=self.conversation_id).update(updated_at=timezone.now())

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "sources": self.sources or [],
            "tool_calls": self.tool_calls or [],
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "is_deleted": self.is_deleted,
            "created_at": _date_to_iso(self.created_at),
            "blocks": [b.to_dict() for b in self.blocks.all()],
            "attachments": [a.to_dict() for a in self.attachments.all()],
        }
