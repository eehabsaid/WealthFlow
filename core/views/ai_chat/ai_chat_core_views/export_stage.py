"""Chat stage 1a: a bare "export it to Excel" / "and as a PDF?" turns the previous answer into the requested files
(no model call). Data questions that also ask for a file are answered normally and finalize_success attaches the
links to their own answer."""

from __future__ import annotations

from typing import Any

from core.services.ai.exports import FOLLOWUP_TOOL, is_pure_followup, previous_answer
from core.services.ai.query_engine import route as route_question
from core.services.ai.query_engine.labels import t as label
from core.services.ai.query_engine.lexicon import language

from .response_finalizer import finalize_success


def export_followup_response(*, cache_mgr: Any, progress_key: Any, conversation: Any, user_msg: Any, user_text: str, route_text: str,
                             understanding: Any, request: Any, trace: Any):
    """The JsonResponse for a pure export follow-up, or None when the message is a data question / new request."""
    previous_text = conversation.messages.filter(role="user", is_deleted=False).exclude(id=user_msg.id) \
        .order_by("-id").values_list("content", flat=True).first() or ""
    if not is_pure_followup(route_question(route_text, previous=previous_text), understanding, route_text):
        return None
    target = previous_answer(conversation, user_msg.id)
    lang = language(user_text)
    trace.skip_remaining("export_followup")
    trace.log_summary()
    return finalize_success(
        cache_mgr, progress_key, conversation, user_msg, user_text,
        label(lang, "export_followup" if target else "export_nothing"),
        [{"tool": FOLLOWUP_TOOL, "target_message_id": target.id if target else None}], [], request,
        export_target=target, offer_export=target is not None,
    )
