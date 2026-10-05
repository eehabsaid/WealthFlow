"""Final persistence and response assembly for AIChatView.

Pure code motion from the original ai_chat_core_views.py — same logic, same
order of operations, only relocated for file-size compliance.
"""

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse

from core.models import AIMessage
from core.services.ai.tools.defs import AI_TOOL_REGISTRY
from core.views.ai_chat.response_sanitizer import strip_latex, strip_leaked_control_tokens


def json_safe(value):
    """Round-trip through JSON so Decimal / date / datetime / UUID / set values (tool results, agent
    steps) can never break the JSONField save or the response. Non-serialisable leftovers become str."""
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder, default=str))


def finalize_success(cache_mgr, progress_key, conversation, user_msg, user_text,
                      content_str, executed_tool_calls, sources, request, extra=None):
    """Persist the assistant reply, extract knowledge, and build the response."""
    # Save successful assistant response with full tool execution audit trail
    content_str = strip_leaked_control_tokens(content_str, set(AI_TOOL_REGISTRY.keys()))
    content_str = strip_latex(content_str)
    executed_tool_calls = json_safe(executed_tool_calls or [])
    sources = json_safe(sources or [])
    meter = getattr(request, "_ai_token_meter", None)  # set by AIChatView; feeds the monthly token limit
    ai_msg = AIMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content=content_str,
        sources=sources,
        tool_calls=executed_tool_calls,
        prompt_tokens=meter.prompt if meter else None,
        completion_tokens=meter.completion if meter else None,
    )

    # Mark progress as done with message_id now that it is saved in history
    cache_mgr.set(
        progress_key,
        {
            "status": "done",
            "message_id": ai_msg.id,
        },
        ttl_seconds=120.0,
    )

    # Extract and persist long-term knowledge from this conversation turn
    try:
        from core.services.ai.knowledge_engine import AIKnowledgeEngine
        AIKnowledgeEngine.extract_knowledge_from_conversation(
            user=request.user,
            user_query=user_text,
            ai_response=content_str,
        )
    except Exception:
        pass  # Knowledge extraction is non-critical — never fail a chat response

    try:
        # Per-user learned notes (teach / correction), scoped to this user only
        from core.services.ai.knowledge_engine import AIKnowledgeEngine
        prev_assistant = (
            conversation.messages.filter(role="assistant", is_deleted=False)
            .exclude(id=ai_msg.id).order_by("-id").first()
        )
        prev_user = (
            conversation.messages.filter(role="user", is_deleted=False)
            .exclude(id=user_msg.id).order_by("-id").first()
        )
        AIKnowledgeEngine.record_user_notes_from_turn(
            user=request.user,
            user_text=user_text,
            previous_question=prev_user.content if prev_user else "",
            previous_used_tools=bool(prev_assistant and prev_assistant.tool_calls),
        )
    except Exception:
        pass  # Knowledge extraction is non-critical — never fail a chat response

    # Update conversation title if default
    if conversation.title in ("New Conversation", ""):
        conversation.title = user_text[:30] + ("..." if len(user_text) > 30 else "")
        conversation.save(update_fields=["title", "updated_at"])

    payload = {
        "ok": True,
        "conversation_id": conversation.id,
        "user_message": user_msg.to_dict(),
        "message": ai_msg.to_dict(),
        "sources": sources,
    }
    if extra:
        payload.update(extra)  # e.g. {"pipeline": trace} when ai_pipeline_debug is on
    return JsonResponse(payload, encoder=DjangoJSONEncoder)
