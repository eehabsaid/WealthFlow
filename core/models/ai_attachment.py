from django.contrib.auth.models import User
from django.db import models


class AIAttachment(models.Model):
    """A file the user attached to a chat message. Text is extracted by code when it is uploaded (table, PDF, Word, text);
    pictures are kept as bytes and sent to the model as images. Per user, never shared."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_attachments")
    message = models.ForeignKey("AIMessage", on_delete=models.CASCADE, null=True, blank=True, related_name="attachments")
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=10)            # table | text | image
    mime = models.CharField(max_length=100, blank=True, default="")
    size = models.IntegerField(default=0)
    text = models.TextField(blank=True, default="")   # extracted text (and, for tables, the facts the app computed)
    data = models.BinaryField(null=True, blank=True)  # pictures only
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def to_dict(self):
        return {"id": self.id, "name": self.name, "kind": self.kind, "size": self.size}
