"""Context assembly and provider-generation helpers for AIChatView.

Pure code motion from the original ai_chat_core_views.py — same logic, same
order of operations, only relocated for file-size compliance.
"""

from django.http import JsonResponse

from core.models import AIMessage, AppSettings
from core.services.ai.context_builder_service import ContextBuilderService
from core.services.ai.tools import get_registered_tool_schemas
from core.services.ai.tools.defs import AI_TOOL_REGISTRY
from core.views.ai_chat.ai_chat_helpers import _aiT_fallback_no_answer
from core.views.ai_chat.fake_tool_call_recovery import extract_fake_tool_call


def build_context(request, conversation, user_msg, user_text):
    """Fetch prior messages and assemble the provider message sequence."""
    try:
        history_window_size = int(AppSettings.get("ai_history_window", "10"))
    except (ValueError, TypeError):
        history_window_size = 10

    # Fetch prior non-deleted messages (excluding current message)
    prior_messages = list(
        conversation.messages.filter(is_deleted=False)
        .exclude(id=user_msg.id)
        .order_by("-created_at")[:history_window_size]
    )
    prior_messages.reverse()

    builder = ContextBuilderService()
    messages_seq, sources = builder.assemble_messages(user_text, prior_messages, user=request.user)
    return messages_seq, sources


def initial_generate(provider, messages_seq, question_domain):
    """Run the first provider call, retrying once if the reply is silently empty."""
    tools_param = None
    if getattr(provider, "supports_tools", False):
        tools_param = get_registered_tool_schemas(domain=question_domain)

    # ── Initial provider call ─────────────────────────────────────────────
    res = provider.generate(messages_seq, tools=tools_param)
    error_str = res.get("error")
    content_str = res.get("content", "")
    tool_calls_req = res.get("tool_calls") or []

    # ── Recover from a local-model failure mode: writing a fake tool call
    # as plain-text JSON instead of real structured function-calling (see
    # fake_tool_call_recovery.py). Without this, the call is silently
    # dropped and the fabricated narration is saved as the final answer.
    if not tool_calls_req and not error_str:
        fake_call = extract_fake_tool_call(content_str, set(AI_TOOL_REGISTRY.keys()))
        if fake_call:
            tool_calls_req = [fake_call]
            content_str = ""

    if error_str:
        return tools_param, error_str, content_str, tool_calls_req

    # ── Guard against a "silent" empty response ────────────────────────────
    # Some smaller/local models occasionally return no content AND no tool
    # call on the first turn (not an API error — just an unproductive reply).
    # Without this, the investigation loop below never runs (it's gated on
    # tool_calls_req being non-empty) and we'd silently save an empty
    # assistant message. Give the model one explicit nudge before giving up.
    if not content_str.strip() and not tool_calls_req:
        messages_seq.append({
            "role": "system",
            "content": (
                "Your previous reply was empty. You must either call one of the "
                "available tools to investigate the user's question, or provide a "
                "direct text answer. Do not return an empty response."
            ),
        })
        retry_res = provider.generate(messages_seq, tools=tools_param)
        content_str = retry_res.get("content", "") or content_str
        tool_calls_req = retry_res.get("tool_calls") or []

        if not content_str.strip() and not tool_calls_req:
            content_str = _aiT_fallback_no_answer()

    return tools_param, error_str, content_str, tool_calls_req


def build_provider_error_response(cache_mgr, progress_key, conversation, sources, user_msg, error_str):
    """Record the provider-error state, persist the error message, and respond."""
    cache_mgr.set(
        progress_key,
        {"status": "error", "error": error_str},
        ttl_seconds=60.0,
    )
    # Save error response in history to preserve execution record
    ai_msg = AIMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content="",
        sources=sources,
        tool_calls=[],
    )
    return JsonResponse(
        {
            "ok": False,
            "error_key": "ai_error_provider_unavailable",
            "error": error_str,
            "conversation_id": conversation.id,
            "sources": sources,
            "user_message": user_msg.to_dict(),
            "message": ai_msg.to_dict(),
        },
        status=200,
    )
