"""Routes the WealthFlow pack adds to the AI app."""
from django.urls import path

from ai.host import feature_required
from core.ai_pack.views.ai_insights_views import AIInsightsView

urlpatterns = [
    path("api/financial-advisor/ai/insights/", feature_required("allows_ai_workspace")(AIInsightsView.as_view())),
]
