from django.http import JsonResponse
from django.views import View

from core.ai_pack.insights import compute_insights
from ai.views.ai_chat.ai_chat_helpers import _api_auth_required


class AIInsightsView(View):
    """GET /api/financial-advisor/ai/insights/ -> {insights: [...]} computed from the signed-in user's own data."""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        return JsonResponse({"insights": compute_insights(request.user)})
