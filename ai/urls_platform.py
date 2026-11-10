from django.urls import path
from ai.views.ai_platform.knowledge_views import AIPlatformKnowledgeDetailView, AIPlatformKnowledgeView
from ai.views.ai_prompt_views import AIPromptCategoryListView, AIPromptDetailView, AIPromptDuplicateView, AIPromptFavoriteView, AIPromptListView, AIPromptUseView
from ai.host import feature_required

_ai = feature_required("allows_ai_workspace")

urlpatterns = [
    path(
        "api/ai-platform/knowledge/",
        _ai(AIPlatformKnowledgeView.as_view()),
    ),
    path(
        "api/ai-platform/knowledge/<int:pk>/",
        _ai(AIPlatformKnowledgeDetailView.as_view()),
    ),
    # ── AI Prompt Library ────────────────────────────────────────────────────
    path(
        "api/ai-platform/prompts/categories/",
        _ai(AIPromptCategoryListView.as_view()),
    ),
    path(
        "api/ai-platform/prompts/",
        _ai(AIPromptListView.as_view()),
    ),
    path(
        "api/ai-platform/prompts/<int:pk>/",
        _ai(AIPromptDetailView.as_view()),
    ),
    path(
        "api/ai-platform/prompts/<int:pk>/favorite/",
        _ai(AIPromptFavoriteView.as_view()),
    ),
    path(
        "api/ai-platform/prompts/<int:pk>/use/",
        _ai(AIPromptUseView.as_view()),
    ),
    path(
        "api/ai-platform/prompts/<int:pk>/duplicate/",
        _ai(AIPromptDuplicateView.as_view()),
    ),
]
