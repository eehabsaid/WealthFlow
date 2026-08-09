"""
AI Financial Advisor Chat Views.

Handles AI chat interactions, conversation management, and history retrieval.
Chat views exclusively invoke get_active_ai_provider() and ContextBuilderService,
ensuring total decoupling from concrete AI providers and financial services.
"""

import json
import time
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.integrations.ai_provider import get_active_ai_provider
from core.models import AppSettings, AIConversation, AIMessage
from core.services.ai.cache_manager import AICacheManager
from core.services.ai.context_builder_service import ContextBuilderService
from core.services.ai.tools import (
    get_registered_tool_schemas,
    validate_and_execute_tool,
)

# Maximum number of tool-call/response iterations per user message.
# Tunable: increase cautiously on GPU hardware, decrease if CPU latency is unacceptable.
MAX_TOOL_ITERATIONS = 8

# Total wall-clock budget (seconds) for the full investigation loop.
# Readable from AppSettings as "ai_total_loop_timeout"; defaults to 300s (5 minutes).
# This caps the worst-case (MAX_TOOL_ITERATIONS × per-call timeout) accumulation.
LOOP_TOTAL_TIMEOUT_SECONDS = 300


def _get_loop_timeout() -> int:
    """Read the total loop wall-clock budget from AppSettings with safe fallback."""
    try:
        return max(30, int(AppSettings.get("ai_total_loop_timeout", str(LOOP_TOTAL_TIMEOUT_SECONDS))))
    except (ValueError, TypeError):
        return LOOP_TOTAL_TIMEOUT_SECONDS


def _parse_tool_call(tc: dict) -> tuple[str, dict]:
    """Extract (fn_name, fn_args) from a raw tool_call dict. Returns ('', {}) on failure."""
    if not isinstance(tc, dict):
        return "", {}
    fn_info = tc.get("function", {}) if isinstance(tc.get("function"), dict) else {}
    fn_name = str(fn_info.get("name") or tc.get("name") or "").strip()
    fn_args = fn_info.get("arguments") or tc.get("arguments") or {}
    if isinstance(fn_args, str):
        try:
            fn_args = json.loads(fn_args)
        except Exception:
            fn_args = {}
    if not isinstance(fn_args, dict):
        fn_args = {}
    return fn_name, fn_args


def _fingerprint(fn_name: str, fn_args: dict) -> str:
    """Stable fingerprint of a (tool_name, arguments) pair for repeat-call detection."""
    return f"{fn_name}:{json.dumps(fn_args, sort_keys=True, default=str)}"


def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None


@method_decorator(csrf_exempt, name="dispatch")
class AIChatView(View):
    """
    Endpoint for sending messages to AI Financial Advisor.
    URL: POST /api/financial-advisor/ai/chat/

    Implements a bounded multi-step investigation loop (up to MAX_TOOL_ITERATIONS)
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

        # ── Bounded multi-step investigation loop ─────────────────────────────
        executed_tool_calls = []
        loop_start = time.monotonic()
        loop_timeout = _get_loop_timeout()
        seen_fingerprints: set[str] = set()

        # Progress cache for frontend polling
        cache_mgr = AICacheManager()
        progress_key = f"ai_loop_progress:{request.user.id}:{conversation.id}"

        iteration = 0
        while tool_calls_req and isinstance(tool_calls_req, list) and iteration < MAX_TOOL_ITERATIONS:
            # ── Wall-clock budget check ───────────────────────────────────────
            elapsed = time.monotonic() - loop_start
            if elapsed >= loop_timeout:
                messages_seq.append({
                    "role": "system",
                    "content": (
                        f"INVESTIGATION TIMEOUT: The total investigation budget of {loop_timeout}s was reached "
                        f"after {iteration} step(s). Provide your best answer using only the information "
                        "already gathered above. Do not call any further tools."
                    ),
                })
                fallback_res = provider.generate(messages_seq, tools=None)
                if fallback_res.get("content"):
                    content_str = fallback_res["content"]
                break

            iteration += 1
            tc = tool_calls_req[0]
            fn_name, fn_args = _parse_tool_call(tc)

            if not fn_name:
                # Malformed tool call — stop loop, use content already in content_str
                break

            # Auto-populate search_query for query_application_data if missing
            if fn_name == "query_application_data" and not fn_args.get("search_query"):
                fn_args["search_query"] = user_text

            # ── Repeat-call prevention ────────────────────────────────────────
            fp = _fingerprint(fn_name, fn_args)
            if fp in seen_fingerprints:
                messages_seq.append({
                    "role": "system",
                    "content": (
                        f"DUPLICATE TOOL CALL BLOCKED: You already called '{fn_name}' with these exact "
                        "arguments in a previous step. The result is already in the conversation above. "
                        "Use that existing result to answer the user's question, or call a different tool "
                        "to gather additional information."
                    ),
                })
                # Count as one iteration to prevent infinite loops on this failure mode
                tool_calls_req = []
                # Ask the model to proceed — still offering tools so it can pivot to a different one
                next_res = provider.generate(messages_seq, tools=tools_param)
                content_str = next_res.get("content", content_str)
                tool_calls_req = next_res.get("tool_calls") or []
                continue

            seen_fingerprints.add(fp)

            # ── Publish progress state for frontend polling ───────────────────
            cache_mgr.set(
                progress_key,
                {
                    "step": iteration,
                    "max_steps": MAX_TOOL_ITERATIONS,
                    "tool": fn_name,
                    "status": "running",
                    "elapsed_s": round(time.monotonic() - loop_start, 1),
                },
                ttl_seconds=120.0,
            )

            # ── Execute tool via existing validated pipeline ──────────────────
            audit_rec, tool_res = validate_and_execute_tool(fn_name, fn_args, request.user)
            audit_rec["step"] = iteration
            audit_rec["total_budget_elapsed_s"] = round(time.monotonic() - loop_start, 1)
            executed_tool_calls.append(audit_rec)

            # Append tool result to messages for the next model call
            tool_summary_str = json.dumps(tool_res, default=str)
            messages_seq.append(
                {
                    "role": "system",
                    "content": (
                        f"STEP {iteration}/{MAX_TOOL_ITERATIONS} — TOOL CALLED: '{fn_name}'\n"
                        f"TOOL EXECUTION RESULT: {tool_summary_str}\n\n"
                        f"If you have enough information to answer the user's query '{user_text}', "
                        "provide your final answer now. Otherwise, call the next most relevant tool."
                    ),
                }
            )

            # ── Next model call — tools still offered ─────────────────────────
            next_res = provider.generate(messages_seq, tools=tools_param)
            if next_res.get("error"):
                # Provider error mid-loop — stop and use what we have
                break

            content_str = next_res.get("content", content_str)
            tool_calls_req = next_res.get("tool_calls") or []

        # ── Cap exhaustion fallback ───────────────────────────────────────────
        # If the loop exhausted MAX_TOOL_ITERATIONS without a text-only final answer
        if iteration >= MAX_TOOL_ITERATIONS and tool_calls_req:
            messages_seq.append({
                "role": "system",
                "content": (
                    f"You have used the maximum number of investigation steps ({MAX_TOOL_ITERATIONS}). "
                    "Provide your best answer using only the information already gathered above. "
                    "Do not execute further tools."
                ),
            })
            final_res = provider.generate(messages_seq, tools=None)
            if final_res.get("content"):
                content_str = final_res["content"]

        # Clear progress state
        cache_mgr.set(progress_key, {"status": "done"}, ttl_seconds=10.0)

        # Save successful assistant response with full tool execution audit trail
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
class AIProgressView(View):
    """
    Lightweight progress polling endpoint for the multi-step investigation loop.
    URL: GET /api/financial-advisor/ai/progress/?conversation_id=<id>

    Returns the current loop step, tool name, and elapsed time for the requesting
    user's active investigation. The frontend polls this every 2 seconds while
    loading to update the typing bubble with live step information.

    Auth: session-authenticated (same pattern as all other AI endpoints).
    Ownership: progress key is scoped to user.id × conversation.id — a different
    user cannot see another user's progress even if they guess the conversation ID.
    Additionally, the conversation ownership is explicitly verified below.
    """

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        conversation_id = request.GET.get("conversation_id", "")
        try:
            conv_id = int(conversation_id)
        except (ValueError, TypeError):
            return JsonResponse({"status": "idle"})

        # Explicit ownership check: the conversation must belong to this user
        try:
            AIConversation.objects.get(id=conv_id, user=request.user, is_deleted=False)
        except AIConversation.DoesNotExist:
            # Return idle rather than 403 to avoid leaking conversation existence
            return JsonResponse({"status": "idle"})

        cache_mgr = AICacheManager()
        progress_key = f"ai_loop_progress:{request.user.id}:{conv_id}"
        state = cache_mgr.get(progress_key)

        if not state:
            return JsonResponse({"status": "idle"})

        return JsonResponse(state)


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
