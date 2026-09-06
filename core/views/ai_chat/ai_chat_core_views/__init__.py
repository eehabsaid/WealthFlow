"""AI Financial Advisor — core chat endpoint (AIChatView).

Package layout
--------------
Split into a package (was a single >200-line module) per the project's
200-line-per-file convention.

- conversation_setup.py    conversation lookup, progress-cache bootstrap
- generation_pipeline.py   context assembly, provider-generation + retry
- response_finalizer.py    persistence, knowledge extraction, response build

`get_active_ai_provider` is imported and invoked directly in this module
(not delegated to a sibling) so that the existing test-suite patch target
`core.views.ai_chat.ai_chat_core_views.get_active_ai_provider` keeps
resolving correctly.
"""

import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.integrations.ai_provider import get_active_ai_provider
from core.services.ai.cache_manager import AICacheManager
from core.views.ai_chat.ai_chat_helpers import _api_auth_required
from core.views.ai_chat.ai_chat_loop import run_tool_investigation_loop

from .conversation_setup import (
    build_provider_disabled_response,
    init_progress,
    resolve_conversation,
    save_user_message,
)
from .generation_pipeline import build_context, build_provider_error_response, initial_generate
from .response_finalizer import finalize_success

__all__ = ["AIChatView"]


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

        conversation = resolve_conversation(request, body, user_text)

        # MANDATORY REQUIREMENT: Always save user message to history FIRST
        user_msg = save_user_message(conversation, user_text)

        # Publish initial running state immediately so polling sees progress right away
        cache_mgr = AICacheManager()
        progress_key = init_progress(cache_mgr, request, conversation)

        # Check if AI provider is active
        provider = get_active_ai_provider()
        if not provider:
            return build_provider_disabled_response(cache_mgr, progress_key, conversation, user_msg)

        # Build context and messages sequence
        messages_seq, sources = build_context(request, conversation, user_msg, user_text)

        question_domain = str(body.get("question_domain", "")).strip() or None

        tools_param, error_str, content_str, tool_calls_req = initial_generate(
            provider, messages_seq, question_domain
        )

        if error_str:
            return build_provider_error_response(
                cache_mgr, progress_key, conversation, sources, user_msg, error_str
            )

        # ── Bounded multi-step investigation loop ─────────────────────────────
        content_str, executed_tool_calls = run_tool_investigation_loop(
            provider, messages_seq, tools_param, tool_calls_req, content_str,
            user_text, request.user, conversation.id,
        )

        return finalize_success(
            cache_mgr, progress_key, conversation, user_msg, user_text,
            content_str, executed_tool_calls, sources, request,
        )
