import json

from django.http import JsonResponse
from django.views import View

from core.services.ai.app_knowledge import record_feedback
from core.validators.json_body import parse_json_body
from core.views.ai_chat.ai_chat_helpers import _api_auth_required


class AIMessageFeedbackView(View):
    """Thumbs up / down on one assistant answer.
    URL: POST /api/financial-advisor/ai/messages/<id>/feedback/   body {"rating": 1 | -1 | 0}  (0 clears)
    Thumbs-up answers to how/where/should questions become retrievable examples for this user's similar
    questions; thumbs-down answers are never reused."""

    def post(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            body = parse_json_body(request)
            rating = int(body.get("rating"))
        except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
            return JsonResponse({"error": "invalid_rating"}, status=400)
        result = record_feedback(request.user, pk, rating)
        if not result["ok"]:
            return JsonResponse({"error": result["error"]}, status=404 if result["error"] == "not_found" else 400)
        return JsonResponse(result)


class AIFeedbackListView(View):
    """The requesting user's rated answers (newest first, max 100).
    URL: GET /api/financial-advisor/ai/feedback/"""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.models import AIAnswerFeedback

        rows = AIAnswerFeedback.objects.filter(owner=request.user)[:100]
        return JsonResponse({"items": [{**r.to_dict(), "question": r.question[:300], "answer": r.answer[:600]} for r in rows]})
