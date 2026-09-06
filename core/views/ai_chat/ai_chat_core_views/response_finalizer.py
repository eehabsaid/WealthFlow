"""Final persistence and response assembly for AIChatView.

Pure code motion from the original ai_chat_core_views.py — same logic, same
order of operations, only relocated for file-size compliance.
"""

from django.http import JsonResponse

from core.models import AIMessage
from core.services.ai.tools.defs import AI_TOOL_REGISTRY
from core.views.ai_chat.response_sanitizer import strip_latex, strip_leaked_control_tokens


def finalize_success(cache_mgr, progress_key, conversation, user_msg, user_text,
                      content_str, executed_tool_calls, sources, request):
    """Persist the assistant reply, extract knowledge, and build the response."""
    # Save successful assistant response with full tool execution audit trail
    content_str = strip_leaked_control_tokens(content_str, set(AI_TOOL_REGISTRY.keys()))
    content_str = strip_latex(content_str)
    ai_msg = AIMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content=content_str,
        sources=sources,
        tool_calls=executed_tool_calls,
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

    # Update conversation title if default
    if conversation.title in ("New Conversation", ""):
        conversation.title = user_text[:30] + ("..." if len(user_text) > 30 else "")
        conversation.save(update_fields=["title", "updated_at"])

    return JsonResponse(
        {
            "ok": True,
            "conversation_id": conversation.id,
            "user_message": user_msg.to_dict(),
            "message": ai_msg.to_dict(),
            "sources": sources,
        }
    )
