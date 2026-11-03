"""Confirm / cancel an AI action card. Owner-scoped; a card can be decided once. Confirm may carry the values the user edited on the card."""

import json

from django.http import JsonResponse
from django.views import View

from core.services.ai.actions import decide
from core.views.ai_chat.ai_chat_helpers import _api_auth_required


class AIBlockConfirmView(View):
    """POST /api/financial-advisor/ai/blocks/<id>/confirm/"""

    def post(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            edits = json.loads(request.body or b"{}").get("edits")
        except (ValueError, AttributeError):
            edits = None
        body, status = decide(request.user, pk, True, edits if isinstance(edits, dict) else None)
        return JsonResponse(body, status=status)


class AIBlockCancelView(View):
    """POST /api/financial-advisor/ai/blocks/<id>/cancel/"""

    def post(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        body, status = decide(request.user, pk, False)
        return JsonResponse(body, status=status)
