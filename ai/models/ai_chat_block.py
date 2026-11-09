from django.contrib.auth.models import User
from django.db import models


class AIChatBlock(models.Model):
    """Something the assistant shows UNDER an answer: an action card the user must confirm (add / edit / delete a record),
    or a chart computed from the user's own data. Created by tools during the chat, attached to the answer afterwards.
    Per user, never shared. A card can only change data when the user presses the button on it."""

    KIND_ACTION = "action"
    KIND_CHART = "chart"
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_FAILED = "failed"
    STATUS_READY = "ready"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_chat_blocks")
    message = models.ForeignKey("AIMessage", on_delete=models.CASCADE, null=True, blank=True, related_name="blocks")
    kind = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default="ready")
    payload = models.JSONField(default=dict, blank=True)   # action: {op, record, params, rows}; chart: {type, title, labels, series, unit}
    result = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "core_aichatblock"
        ordering = ["id"]

    def to_dict(self):
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "payload": self.payload or {},
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }
