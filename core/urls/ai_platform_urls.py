from django.urls import path
from .. import views
from core.services.billing import feature_required

_ai = feature_required("allows_ai_workspace")

urlpatterns = [
    path(
        "api/ai-platform/knowledge/",
        _ai(views.AIPlatformKnowledgeView.as_view()),
    ),
    path(
        "api/ai-platform/knowledge/<int:pk>/",
        _ai(views.AIPlatformKnowledgeDetailView.as_view()),
    ),
    path(
        "api/ai-platform/datasets/",
        _ai(views.AIPlatformDatasetView.as_view()),
    ),
    path(
        "api/ai-platform/models/",
        _ai(views.AIPlatformModelView.as_view()),
    ),
    path(
        "api/ai-platform/benchmarks/",
        _ai(views.AIPlatformBenchmarkView.as_view()),
    ),
    # ── AI Prompt Library ────────────────────────────────────────────────────
    path(
        "api/ai-platform/prompts/categories/",
        _ai(views.AIPromptCategoryListView.as_view()),
    ),
    path(
        "api/ai-platform/prompts/",
        _ai(views.AIPromptListView.as_view()),
    ),
    path(
        "api/ai-platform/prompts/<int:pk>/",
        _ai(views.AIPromptDetailView.as_view()),
    ),
    path(
        "api/ai-platform/prompts/<int:pk>/favorite/",
        _ai(views.AIPromptFavoriteView.as_view()),
    ),
    path(
        "api/ai-platform/prompts/<int:pk>/use/",
        _ai(views.AIPromptUseView.as_view()),
    ),
    path(
        "api/ai-platform/prompts/<int:pk>/duplicate/",
        _ai(views.AIPromptDuplicateView.as_view()),
    ),
]
