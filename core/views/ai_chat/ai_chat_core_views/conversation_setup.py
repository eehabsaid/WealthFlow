"""Conversation resolution and progress-cache bootstrap helpers for AIChatView.

Pure code motion from the original ai_chat_core_views.py — same logic, same
order of operations, only relocated for file-size compliance.
"""

import time

from django.http import JsonResponse

from core.models import AIConversation, AIMessage
from core.views.ai_chat.ai_chat_helpers import MAX_TOOL_ITERATIONS


def resolve_conversation(request, body, user_text):
    """Look up an existing conversation by id, or create a new one."""
    conversation_id = body.get("conversation_id")
    conversation = None

    if conversation_id:
        try:
            conversation = AIConversation.objects.get(
                id=int(conversation_id), user=request.user, is_deleted=False
            )
        except (AIConversation.DoesNotExist, ValueError, TypeError):
            conversation = None

    if not conversation:
        title = user_text[:30] + ("..." if len(user_text) > 30 else "")
        conversation = AIConversation.objects.create(user=request.user, title=title)

    return conversation


def save_user_message(conversation, user_text):
    """Persist the user message to history. Must happen before any AI call."""
    return AIMessage.objects.create(
        conversation=conversation,
        role="user",
        content=user_text,
        sources=[],
    )


def init_progress(cache_mgr, request, conversation):
    """Publish the initial 'running' progress state and return its cache key."""
    progress_key = f"ai_loop_progress:{request.user.id}:{conversation.id}"
    cache_mgr.set(
        progress_key,
        {
            "status": "running",
            "step": 0,
            "max_steps": MAX_TOOL_ITERATIONS,
            "tool": "thinking",
            "label": "WealthFlow AI is thinking...",
            "started_at": time.time(),
            "elapsed_s": 0.0,
        },
        ttl_seconds=1800.0,
    )
    return progress_key


def build_provider_disabled_response(cache_mgr, progress_key, conversation, user_msg):
    """Record the provider-disabled error state and build the JSON response."""
    cache_mgr.set(
        progress_key,
        {"status": "error", "error": "AI Provider is disabled or unconfigured."},
        ttl_seconds=60.0,
    )
    return JsonResponse(
        {
            "ok": False,
            "error_key": "ai_chat_disabled_desc",
            "error": "AI Provider is disabled or unconfigured.",
            "conversation_id": conversation.id,
            "user_message": user_msg.to_dict(),
        },
        status=200,
    )
