"""
AI Financial Advisor Chat Views.

Handles AI chat interactions, conversation management, and history retrieval.
Chat views exclusively invoke get_active_ai_provider() and ContextBuilderService,
ensuring total decoupling from concrete AI providers and financial services.
"""

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.integrations.ai_provider import get_active_ai_provider
from core.models import AppSettings, AIConversation, AIMessage
from core.services.ai.context_builder_service import ContextBuilderService
from core.services.ai.tools import (
    get_registered_tool_schemas,
    validate_and_execute_tool,
)


def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None


@method_decorator(csrf_exempt, name="dispatch")
class AIChatView(View):
    """
    Endpoint for sending messages to AI Financial Advisor.
    URL: POST /api/financial-advisor/ai/chat/
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

        # Check if AI provider is active
        provider = get_active_ai_provider()
        if not provider:
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
        messages_seq, sources = builder.assemble_messages(user_text, prior_messages)

        # Tool calling setup
        tools_param = None
        if getattr(provider, "supports_tools", False):
            tools_param = get_registered_tool_schemas()

        # Execute provider call
        res = provider.generate(messages_seq, tools=tools_param)
        error_str = res.get("error")
        content_str = res.get("content", "")
        tool_calls_req = res.get("tool_calls") or []

        if error_str:
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

        executed_tool_calls = []
        # Rule 4: At most ONE tool call per user message turn
        if tool_calls_req and isinstance(tool_calls_req, list):
            tc = tool_calls_req[0]
            if isinstance(tc, dict):
                fn_info = tc.get("function", {}) if isinstance(tc.get("function"), dict) else {}
                fn_name = str(fn_info.get("name") or tc.get("name") or "").strip()
                fn_args = fn_info.get("arguments") or tc.get("arguments") or {}

                audit_rec, tool_res = validate_and_execute_tool(fn_name, fn_args, request.user)
                executed_tool_calls.append(audit_rec)

                # Feed tool result back into context for narration/explanation (without offering tools again)
                tool_summary_str = json.dumps(tool_res, default=str)
                messages_seq.append(
                    {
                        "role": "system",
                        "content": (
                            f"TOOL CALLED: '{fn_name}'\n"
                            f"TOOL EXECUTION RESULT: {tool_summary_str}\n\n"
                            "Instructions: Please summarize, explain, or narrate this real tool result clearly to the user. "
                            "Do not execute further tools."
                        ),
                    }
                )

                # Generate model's natural language narration
                followup_res = provider.generate(messages_seq)
                if followup_res.get("content"):
                    content_str = followup_res["content"]

        # Save successful assistant response with tool execution audit trail
        ai_msg = AIMessage.objects.create(
            conversation=conversation,
            role="assistant",
            content=content_str,
            sources=sources,
            tool_calls=executed_tool_calls,
        )

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


@method_decorator(csrf_exempt, name="dispatch")
class AIConversationListView(View):
    """
    View for listing and creating conversations.
    URL: GET/POST /api/financial-advisor/ai/conversations/
    """

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        conversations = AIConversation.objects.filter(user=request.user, is_deleted=False)
        data = [c.to_dict() for c in conversations]
        return JsonResponse({"conversations": data})

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            body = {}

        title = str(body.get("title", "New Conversation")).strip() or "New Conversation"
        conversation = AIConversation.objects.create(user=request.user, title=title)
        return JsonResponse({"conversation": conversation.to_dict()}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class AIConversationDetailView(View):
    """
    View for viewing or soft-deleting a conversation.
    URL: GET/DELETE /api/financial-advisor/ai/conversations/<int:pk>/
    """

    def get(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            conversation = AIConversation.objects.get(id=pk, user=request.user, is_deleted=False)
        except AIConversation.DoesNotExist:
            return JsonResponse({"error": "Conversation not found"}, status=404)

        messages = conversation.messages.filter(is_deleted=False)
        msg_list = [m.to_dict() for m in messages]

        conv_dict = conversation.to_dict()
        conv_dict["messages"] = msg_list
        return JsonResponse({"conversation": conv_dict})

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            conversation = AIConversation.objects.get(id=pk, user=request.user, is_deleted=False)
        except AIConversation.DoesNotExist:
            return JsonResponse({"error": "Conversation not found"}, status=404)

        # Soft delete conversation and its messages
        conversation.is_deleted = True
        conversation.save(update_fields=["is_deleted", "updated_at"])
        conversation.messages.filter(is_deleted=False).update(is_deleted=True)

        return JsonResponse({"ok": True, "id": pk})
