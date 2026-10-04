from django.conf import settings
from django.db import models

from .ai_message import AIMessage


class AIAnswerFeedback(models.Model):
    """Thumbs up / down on one assistant answer.

    Thumbs-up answers to how/where/should questions (kind="workflow") become retrievable examples for
    similar questions of the SAME owner. Thumbs-down answers are stored (so the UI keeps its state and
    the answer is known-bad) but are never retrieved or reused.
    """

    RATING_UP, RATING_DOWN = 1, -1
    KIND_WORKFLOW, KIND_DATA = "workflow", "data"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_answer_feedback")
    message = models.ForeignKey(AIMessage, on_delete=models.CASCADE, related_name="feedback")
    question = models.TextField()
    answer = models.TextField()
    rating = models.SmallIntegerField(choices=[(1, "Up"), (-1, "Down")])
    kind = models.CharField(max_length=20, default=KIND_DATA)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["owner", "message"], name="uniq_ai_feedback_owner_message")]

    def to_dict(self):
        return {"id": self.id, "message_id": self.message_id, "rating": self.rating, "kind": self.kind}
