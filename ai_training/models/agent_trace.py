from django.conf import settings
from django.db import models


class AgentTrace(models.Model):
    """One recorded Agent-mode run, kept for training-data export.

    `steps` is [{"tool", "arguments", "result"}] in call order, with the tool text exactly as the model saw it.
    `expected` is what code computed from the owner's rows for a generated question (null for a real chat).
    `verdict` is set only by the automatic judges: pending -> kept | dropped (drop_reasons says why).
    The app's AI tools can never read this table: they only see models of the `core` app.
    """

    PENDING, KEPT, DROPPED = "pending", "kept", "dropped"
    SOURCE_GENERATED, SOURCE_CHAT = "generated", "chat"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_traces")
    source = models.CharField(max_length=20, default=SOURCE_CHAT)
    case_key = models.CharField(max_length=120, blank=True, default="", db_index=True)
    attempt = models.PositiveSmallIntegerField(default=1)
    question = models.TextField()
    hint = models.TextField(blank=True, default="")
    language = models.CharField(max_length=20, blank=True, default="")
    model_name = models.CharField(max_length=120, blank=True, default="")
    system_prompt = models.TextField(blank=True, default="")
    tools = models.JSONField(default=list, blank=True)
    steps = models.JSONField(default=list, blank=True)
    answer = models.TextField(blank=True, default="")
    reason = models.CharField(max_length=40, blank=True, default="")
    expected = models.JSONField(null=True, blank=True)
    verdict = models.CharField(max_length=10, default=PENDING, db_index=True)
    drop_reasons = models.JSONField(default=list, blank=True)
    elapsed_s = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"AgentTrace#{self.pk} {self.verdict}"
