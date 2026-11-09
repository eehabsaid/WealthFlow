"""Creating a pending confirmation card; the same card is never shown twice."""

from __future__ import annotations

import json

from ai.models.ai_chat_block import AIChatBlock


def _same_proposal(a: dict, b: dict) -> bool:
    """Two cards ask for the same change (text compared ignoring upper/lower case), so a model that proposes twice shows one card."""
    norm = lambda payload: json.dumps(payload, sort_keys=True, default=str).lower()  # noqa: E731
    return norm(a) == norm(b)


def make_card(user, payload: dict) -> dict:
    """Tool result for a proposal: a new pending card, or the identical one already waiting under this answer."""
    open_cards = AIChatBlock.objects.filter(user=user, kind=AIChatBlock.KIND_ACTION, status=AIChatBlock.STATUS_PENDING, message__isnull=True)
    block = next((b for b in open_cards if _same_proposal(b.payload, payload)), None)
    if block is not None:
        return {"ok": True, "pending_confirmation": True, "card_id": block.id, "duplicate": True,
                "note": "This exact card is already shown. Do NOT propose it again. Tell the user briefly to press Confirm."}
    block = AIChatBlock.objects.create(user=user, kind=AIChatBlock.KIND_ACTION, status=AIChatBlock.STATUS_PENDING, payload=payload)
    return {"ok": True, "pending_confirmation": True, "card_id": block.id,
            "note": "A confirmation card is now shown under your answer. NOTHING is saved yet. Tell the user briefly what the card will do and that they must press Confirm. Never say it is done."}
