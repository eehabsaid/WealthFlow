from django.urls import path
from .. import views
from core.services.billing import feature_required
from core.views.ai_chat.ai_agent_views import AIChatModeView, AIStopView
from core.views.ai_chat.ai_memory_views import AIMemoryDetailView, AIMemoryListView
from core.views.ai_speech.voice_stream_views import VoiceChatView, VoiceSentencePollView
from core.views.ai_chat.ai_insights_views import AIInsightsView
from core.views.ai_chat.ai_attachment_views import AIAttachmentDetailView, AIAttachmentUploadView
from core.views.ai_chat.ai_blocks_views import AIBlockCancelView, AIBlockConfirmView
from core.views.ai_chat.ai_chat_manage_views import AIConversationSearchView, AIMessageRewindView

urlpatterns = [
    path(
        "api/financial-advisor/cash-flow-forecast/",
        views.CashFlowForecastView.as_view(),
    ),
    path(
        "api/financial-advisor/cash-flow-custom-projection/",
        views.CashFlowCustomProjectionView.as_view(),
    ),
    path(
        "api/financial-advisor/wealth-growth-forecast/",
        views.WealthGrowthForecastView.as_view(),
    ),
    path(
        "api/financial-advisor/overview/",
        views.OverviewView.as_view(),
    ),
    path(
        "api/financial-advisor/portfolio-optimizer/",
        views.PortfolioOptimizerView.as_view(),
    ),
    path(
        "api/financial-advisor/risk-analysis/",
        views.RiskAnalysisView.as_view(),
    ),
    path(
        "api/financial-advisor/spending-intelligence/",
        views.SpendingIntelligenceView.as_view(),
    ),
    path(
        "api/financial-advisor/opportunity-detection/",
        views.OpportunityDetectionView.as_view(),
    ),
    path(
        "api/financial-advisor/performance/",
        views.PerformanceView.as_view(),
    ),
    path(
        "api/financial-advisor/what-if-simulator/",
        views.WhatIfSimulatorView.as_view(),
    ),
    path(
        "api/financial-advisor/scenario-planner/compare/",
        views.ScenarioComparisonView.as_view(),
    ),
    path(
        "api/scenarios/event-definitions/",
        views.ScenarioEventDefinitionsView.as_view(),
    ),
    path(
        "api/scenarios/",
        views.ScenarioListCreateView.as_view(),
    ),
    path(
        "api/scenarios/<int:pk>/",
        views.ScenarioDetailView.as_view(),
    ),
    path(
        "api/scenarios/<int:pk>/events/",
        views.ScenarioEventListCreateView.as_view(),
    ),
    path(
        "api/scenarios/<int:pk>/events/<int:event_id>/",
        views.ScenarioEventDetailView.as_view(),
    ),
    path(
        "api/scenarios/<int:pk>/duplicate/",
        views.ScenarioDuplicateView.as_view(),
    ),
    path(
        "api/financial-advisor/goal-planning/",
        views.GoalPlanningView.as_view(),
    ),
    path("api/financial-advisor/ai/speech/capabilities/", feature_required("allows_ai_workspace")(views.SpeechCapabilitiesView.as_view())),
    path("api/financial-advisor/ai/speech/transcribe/", feature_required("allows_ai_workspace")(views.SpeechTranscribeView.as_view())),
    path("api/financial-advisor/ai/speech/synthesize/", feature_required("allows_ai_workspace")(views.SpeechSynthesizeView.as_view())),
    path(
        "api/financial-advisor/ai/chat/",
        feature_required("allows_ai_workspace")(views.AIChatView.as_view()),
    ),
    path(
        "api/financial-advisor/ai/chat/voice/",
        feature_required("allows_ai_workspace")(VoiceChatView.as_view()),
    ),
    path(
        "api/financial-advisor/ai/speech/voice-chunks/<uuid:turn_id>/",
        feature_required("allows_ai_workspace")(VoiceSentencePollView.as_view()),
    ),
    path(
        "api/financial-advisor/ai/conversations/",
        feature_required("allows_ai_workspace")(views.AIConversationListView.as_view()),
    ),
    path("api/financial-advisor/ai/insights/", feature_required("allows_ai_workspace")(AIInsightsView.as_view())),
    path("api/financial-advisor/ai/attachments/", feature_required("allows_ai_workspace")(AIAttachmentUploadView.as_view())),
    path("api/financial-advisor/ai/attachments/<int:pk>/", feature_required("allows_ai_workspace")(AIAttachmentDetailView.as_view())),
    path("api/financial-advisor/ai/blocks/<int:pk>/confirm/", feature_required("allows_ai_workspace")(AIBlockConfirmView.as_view())),
    path("api/financial-advisor/ai/blocks/<int:pk>/cancel/", feature_required("allows_ai_workspace")(AIBlockCancelView.as_view())),
    path(
        "api/financial-advisor/ai/conversations/search/",
        feature_required("allows_ai_workspace")(AIConversationSearchView.as_view()),
    ),
    path(
        "api/financial-advisor/ai/messages/<int:pk>/rewind/",
        feature_required("allows_ai_workspace")(AIMessageRewindView.as_view()),
    ),
    path(
        "api/financial-advisor/ai/conversations/<int:pk>/",
        feature_required("allows_ai_workspace")(views.AIConversationDetailView.as_view()),
    ),
    path(
        "api/financial-advisor/ai/feedback/",
        feature_required("allows_ai_workspace")(views.AIFeedbackListView.as_view()),
    ),
    path(
        "api/financial-advisor/ai/messages/<int:pk>/export/<str:fmt>/",
        feature_required("allows_ai_workspace")(views.AIMessageExportView.as_view()),
        name="ai-message-export",
    ),
    path(
        "api/financial-advisor/ai/messages/<int:pk>/feedback/",
        feature_required("allows_ai_workspace")(views.AIMessageFeedbackView.as_view()),
    ),
    path(
        "api/financial-advisor/ai/progress/",
        feature_required("allows_ai_workspace")(views.AIProgressView.as_view()),
    ),
    path(
        "api/financial-advisor/ai/chat-mode/",
        feature_required("allows_ai_workspace")(AIChatModeView.as_view()),
    ),
    path(
        "api/financial-advisor/ai/memory/",
        feature_required("allows_ai_workspace")(AIMemoryListView.as_view()),
    ),
    path(
        "api/financial-advisor/ai/memory/<int:pk>/",
        feature_required("allows_ai_workspace")(AIMemoryDetailView.as_view()),
    ),
    path(
        "api/financial-advisor/ai/stop/",
        feature_required("allows_ai_workspace")(AIStopView.as_view()),
    ),
]
