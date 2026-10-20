"""Agent mode endpoints: the per-user Ask/Agent switch and the Stop button.

  GET/POST /api/financial-advisor/ai/chat-mode/   {mode: "ask"|"agent"} (remembered per user)
  POST     /api/financial-advisor/ai/stop/        {conversation_id}       (stops that user's running Agent turn)
"""

import json

from django.http import JsonResponse
from django.views import View

from core.models import AIConversation
from core.services.ai.agent import agent_enabled, control, get_chat_mode, set_chat_mode
from core.services.ai.agent.settings import MODES
from core.services.ai.domains import enabled_domains
from core.services.ai.investigation.code_tools import code_access_allowed
from core.validators.json_body import parse_json_body
from core.views.ai_chat.ai_chat_helpers import _api_auth_required


def _state(user) -> dict:
    return {"mode": get_chat_mode(user), "agent_enabled": agent_enabled(), "code_tools": code_access_allowed(user), "domains": list(enabled_domains())}


class AIChatModeView(View):
    def get(self, request):
        return _api_auth_required(request) or JsonResponse(_state(request.user))

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            body = parse_json_body(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)
        mode = str(body.get("mode", "")).strip().lower()
        if mode not in MODES:
            return JsonResponse({"error": f"mode must be one of {list(MODES)}"}, status=400)
        set_chat_mode(request.user, mode)
        return JsonResponse({"ok": True, **_state(request.user)})


class AIStopView(View):
    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            body = parse_json_body(request)
            conversation_id = int(body.get("conversation_id"))
        except (json.JSONDecodeError, TypeError, ValueError):
            return JsonResponse({"error": "conversation_id is required"}, status=400)
        if not AIConversation.objects.filter(id=conversation_id, user=request.user, is_deleted=False).exists():
            return JsonResponse({"ok": False}, status=404)   # never reveal or stop another user's conversation
        control.request_stop(request.user, conversation_id)
        return JsonResponse({"ok": True})
