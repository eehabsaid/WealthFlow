"""Chat stage 0: a message with attached files goes straight to the model with the files' text (and pictures) in front of the
question. Instant answers are skipped on purpose: they would answer from the app's data and ignore the file."""

from __future__ import annotations

from typing import Any

from core.models import AppSettings
from ai.services.attachments import link_to_message, model_input

from ai.views.ai_chat.ai_chat_core_views import image_edit_turn
from ai.views.ai_chat.ai_chat_core_views.generation_pipeline import build_provider_error_response
from ai.views.ai_chat.ai_chat_core_views.response_finalizer import finalize_success

CHARS_PER_TOKEN = 3     # a rough planning figure, not a measurement
CONTEXT_SHARE = 0.6     # the share of the UI-set context size the files may use
HISTORY_TURNS = 6

SYSTEM = ("The user attached file(s) to this message; their text is inside the user message between ATTACHED FILE markers. Answer from the "
          "files. Figures written as 'COMPUTED BY THE APP' are exact: use them and never add up numbers yourself. If the answer is not in "
          "the files, say so. Answer in the language of the question.")


def attachment_response(*, request: Any, body: dict, cache_mgr: Any, progress_key: Any, conversation: Any, user_msg: Any, user_text: str,
                        provider: Any, trace: Any):
    """The JsonResponse for a message with attached files, or None when it has none."""
    attachments = link_to_message(request.user, body.get("attachment_ids"), user_msg)
    if not attachments:
        return None
    try:
        context = int(AppSettings.get("ai_context_size", "4096", user=request.user))
    except (TypeError, ValueError):
        context = 4096
    budget = int(context * CHARS_PER_TOKEN * CONTEXT_SHARE)
    text, images = model_input(user_text, attachments, budget)
    history = [{"role": m.role, "content": m.content} for m in
               conversation.messages.filter(is_deleted=False, role__in=("user", "assistant")).exclude(id=user_msg.id).order_by("-id")[:HISTORY_TURNS][::-1]]
    last = {"role": "user", "content": text}
    if images:
        last["images"] = images
    with_tool = image_edit_turn.offered(provider, attachments)   # a picture is attached and image generation is on: the model may edit it
    messages = [{"role": "system", "content": SYSTEM + (image_edit_turn.system_note(attachments) if with_tool else "")}, *history, last]
    result, executed = (provider.generate(messages, tools=[image_edit_turn.TOOL_DEF["schema"]]) if with_tool else provider.generate(messages)), []
    if with_tool and not result.get("error"):
        result, executed = image_edit_turn.run(provider, request.user, messages, result)
    trace.skip_remaining("attachments")
    trace.log_summary()
    if result.get("error") or not (result.get("content") or "").strip():
        return build_provider_error_response(cache_mgr, progress_key, conversation, [], user_msg, result.get("error") or "empty answer")
    sources = [a.name for a in attachments]
    return finalize_success(cache_mgr, progress_key, conversation, user_msg, user_text, result["content"], executed, sources, request, offer_export=False)
