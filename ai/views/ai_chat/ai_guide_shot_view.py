"""GET /api/financial-advisor/ai/guide-shots/<key>/ -> one guide screenshot (JPEG) from the signed-in user's own folder.
Any other key, or another user's, answers 404."""

from django.http import HttpResponse, JsonResponse
from django.views import View

from ai.services.guide_shots import store
from ai.views.ai_chat.ai_chat_helpers import _api_auth_required


class AIGuideShotView(View):
    def get(self, request, key):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        data = store.read(request.user.pk, key)
        if data is None:
            return JsonResponse({"error": "not_found"}, status=404)
        response = HttpResponse(data, content_type="image/jpeg")
        response["Cache-Control"] = "private, max-age=300"
        response["X-Content-Type-Options"] = "nosniff"
        return response
