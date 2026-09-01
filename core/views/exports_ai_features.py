"""Umbrella re-export for the AI Workspace features domain: chat
conversations (ai_chat_views.py), the platform panels — Knowledge
Base, Dataset Manager, Model Management, Benchmark Results
(ai_platform_views.py) — and the Prompt Library (ai_prompt_views.py).
Distinct from the AI Settings/connection-test views, which live under
settings/ai/ since they back a Settings tab, not a workspace feature.

Whenever ai_chat_views.py, ai_platform_views.py, or ai_prompt_views.py
grow and add/remove a public name, update the imports/__all__ below to
match — this file is what core/views/__init__.py depends on, so no
other file needs to change when those are reorganized internally.
"""

from .ai_chat_views import AIChatView, AIConversationListView, AIConversationDetailView, AIProgressView
from .ai_platform_views import (
    AIPlatformKnowledgeView,
    AIPlatformDatasetView,
    AIPlatformModelView,
    AIPlatformBenchmarkView,
    AIPlatformKnowledgeDetailView,
)
from .ai_prompt_views import (
    AIPromptListView,
    AIPromptDetailView,
    AIPromptFavoriteView,
    AIPromptUseView,
    AIPromptDuplicateView,
    AIPromptCategoryListView,
)

__all__ = [
    "AIChatView",
    "AIConversationListView",
    "AIConversationDetailView",
    "AIProgressView",
    "AIPlatformKnowledgeView",
    "AIPlatformDatasetView",
    "AIPlatformModelView",
    "AIPlatformBenchmarkView",
    "AIPlatformKnowledgeDetailView",
    "AIPromptListView",
    "AIPromptDetailView",
    "AIPromptFavoriteView",
    "AIPromptUseView",
    "AIPromptDuplicateView",
    "AIPromptCategoryListView",
]
