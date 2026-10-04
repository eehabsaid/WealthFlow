"""Record / clear a thumbs up or down on an assistant message (owner checked through the conversation)."""

from __future__ import annotations

from typing import Any

SOURCE_MARK = "app_knowledge"


def record_feedback(user: Any, message_id: int, rating: int) -> dict[str, Any]:
    """rating: 1 up, -1 down, 0 clear. Returns {ok, rating} or {ok: False, error}."""
    from core.models import AIAnswerFeedback, AIMessage

    if rating not in (1, -1, 0):
        return {"ok": False, "error": "invalid_rating"}
    msg = AIMessage.objects.select_related("conversation").filter(
        id=message_id, role="assistant", is_deleted=False, conversation__user=user, conversation__is_deleted=False).first()
    if msg is None:
        return {"ok": False, "error": "not_found"}
    if rating == 0:
        AIAnswerFeedback.objects.filter(owner=user, message=msg).delete()
        return {"ok": True, "rating": 0}
    question = (msg.conversation.messages.filter(role="user", is_deleted=False, id__lt=msg.id).order_by("-id")
                .values_list("content", flat=True).first() or "")
    kind = AIAnswerFeedback.KIND_WORKFLOW if SOURCE_MARK in (msg.sources or []) else AIAnswerFeedback.KIND_DATA
    AIAnswerFeedback.objects.update_or_create(
        owner=user, message=msg, defaults={"question": question, "answer": msg.content, "rating": rating, "kind": kind})
    return {"ok": True, "rating": rating}


def ratings_for(user: Any, message_ids: list[int]) -> dict[int, int]:
    from core.models import AIAnswerFeedback

    return dict(AIAnswerFeedback.objects.filter(owner=user, message_id__in=message_ids).values_list("message_id", "rating"))
