"""Approved Q&A pairs as retrievable examples (owner-scoped; thumbs-down is never returned)."""

from __future__ import annotations

from typing import Any

from core.services.ai.codebase_search import query_tokens

MIN_SHARED, MIN_JACCARD, SCAN_LIMIT, ANSWER_CHARS = 2, 0.4, 300, 600


def find_examples(user: Any, query: str, limit: int = 2) -> list[dict[str, str]]:
    from core.models import AIAnswerFeedback

    if user is None or not getattr(user, "is_authenticated", False):
        return []
    q = query_tokens(query)
    if len(q) < MIN_SHARED:
        return []
    rows = AIAnswerFeedback.objects.filter(owner=user, kind=AIAnswerFeedback.KIND_WORKFLOW).order_by("-updated_at")[:SCAN_LIMIT]
    down = set(AIAnswerFeedback.objects.filter(owner=user, rating=AIAnswerFeedback.RATING_DOWN).values_list("answer", flat=True))
    scored = []
    for row in rows:
        if row.rating != AIAnswerFeedback.RATING_UP or row.answer in down:
            continue
        t = query_tokens(row.question)
        shared = len(q & t)
        jac = shared / max(len(q | t), 1)
        if shared >= MIN_SHARED and jac >= MIN_JACCARD:
            scored.append((jac, row))
    scored.sort(key=lambda s: -s[0])
    return [{"question": r.question[:300], "answer": r.answer[:ANSWER_CHARS]} for _, r in scored[:limit]]
