"""AI Financial Advisor — core chat endpoint (AIChatView)."""

import json
import time

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.integrations.ai_provider import get_active_ai_provider
from core.models import AIConversation, AIMessage, AppSettings
from core.services.ai.cache_manager import AICacheManager
from core.services.ai.context_builder_service import ContextBuilderService
from core.services.ai.tools import get_registered_tool_schemas
from core.views.ai_chat.ai_chat_helpers import (MAX_TOOL_ITERATIONS,
                                                _aiT_fallback_no_answer,
                                                _api_auth_required)
from core.views.ai_chat.ai_chat_loop import run_tool_investigation_loop


@method_decorator(csrf_exempt, name="dispatch")
class AIChatView(View):
    """
    Endpoint for sending messages to AI Financial Advisor.
    URL: POST /api/financial-advisor/ai/chat/

    Implements a bounded multi-step investigation loop (see ai_chat_loop.py)
    so the AI can chain tool calls in sequence — each step informed by the previous
    result — the same way a human investigator works.

    Safety guarantees (CPU-only hardware):
    - Per-call timeout: inherited from ai_timeout AppSettings via OllamaProvider.generate().
    - Total loop budget: LOOP_TOTAL_TIMEOUT_SECONDS wall-clock cap across all iterations.
    - Repeat-call prevention: identical (tool, args) pairs are blocked mid-loop.
    - Graceful fallback: user always receives a text answer; never a hang or silent failure.
    """

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        user_text = str(body.get("message", "")).strip()
        if not user_text:
            return JsonResponse({"error": "Message text cannot be empty"}, status=400)

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

        # MANDATORY REQUIREMENT: Always save user message to history FIRST
        user_msg = AIMessage.objects.create(
            conversation=conversation,
            role="user",
            content=user_text,
            sources=[],
        )

        # Publish initial running state immediately so polling sees progress right away
        cache_mgr = AICacheManager()
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

        # Check if AI provider is active
        provider = get_active_ai_provider()
        if not provider:
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

        # Read history window size from AppSettings
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

        # Build context and messages sequence
        builder = ContextBuilderService()
        messages_seq, sources = builder.assemble_messages(user_text, prior_messages, user=request.user)

        question_domain = str(body.get("question_domain", "")).strip() or None

        # Tool calling setup
        tools_param = None
        if getattr(provider, "supports_tools", False):
            tools_param = get_registered_tool_schemas(domain=question_domain)

        # ── Initial provider call ─────────────────────────────────────────────
        res = provider.generate(messages_seq, tools=tools_param)
        error_str = res.get("error")
        content_str = res.get("content", "")
        tool_calls_req = res.get("tool_calls") or []

        if error_str:
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

        # ── Bounded multi-step investigation loop ─────────────────────────────
        content_str, executed_tool_calls = run_tool_investigation_loop(
            provider, messages_seq, tools_param, tool_calls_req, content_str,
            user_text, request.user, conversation.id,
        )

        # Save successful assistant response with full tool execution audit trail
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
