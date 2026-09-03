from django.urls import path
from .. import views

urlpatterns = [
    path(
        "api/ai-platform/knowledge/",
        views.AIPlatformKnowledgeView.as_view(),
    ),
    path(
        "api/ai-platform/knowledge/<int:pk>/",
        views.AIPlatformKnowledgeDetailView.as_view(),
    ),
    path(
        "api/ai-platform/datasets/",
        views.AIPlatformDatasetView.as_view(),
    ),
    path(
        "api/ai-platform/models/",
        views.AIPlatformModelView.as_view(),
    ),
    path(
        "api/ai-platform/benchmarks/",
        views.AIPlatformBenchmarkView.as_view(),
    ),
    # ── AI Prompt Library ────────────────────────────────────────────────────
    path(
        "api/ai-platform/prompts/categories/",
        views.AIPromptCategoryListView.as_view(),
    ),
    path(
        "api/ai-platform/prompts/",
        views.AIPromptListView.as_view(),
    ),
    path(
        "api/ai-platform/prompts/<int:pk>/",
        views.AIPromptDetailView.as_view(),
    ),
    path(
        "api/ai-platform/prompts/<int:pk>/favorite/",
        views.AIPromptFavoriteView.as_view(),
    ),
    path(
        "api/ai-platform/prompts/<int:pk>/use/",
        views.AIPromptUseView.as_view(),
    ),
    path(
        "api/ai-platform/prompts/<int:pk>/duplicate/",
        views.AIPromptDuplicateView.as_view(),
    ),
]
