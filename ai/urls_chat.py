"""AI workspace routes: chat, conversations, memory, speech, voice, blocks."""

from django.urls import path

from core.services.billing import feature_required
from ai.views.ai_chat.ai_agent_views import AIChatModeView, AIStopView
from ai.views.ai_chat.ai_attachment_views import AIAttachmentDetailView, AIAttachmentUploadView
from ai.views.ai_chat.ai_blocks_views import AIBlockCancelView, AIBlockConfirmView
from ai.views.ai_chat.ai_chat_core_views import AIChatView
from ai.views.ai_chat.ai_chat_manage_views import AIConversationSearchView, AIMessageRewindView
from ai.views.ai_chat.ai_conversation_views import AIConversationDetailView, AIConversationListView, AIProgressView
from ai.views.ai_chat.ai_export_views import AIMessageExportView
from ai.views.ai_chat.ai_feedback_views import AIFeedbackListView, AIMessageFeedbackView
from ai.views.ai_chat.ai_insights_views import AIInsightsView
from ai.views.ai_chat.ai_memory_views import AIMemoryDetailView, AIMemoryListView
from ai.views.ai_speech.speech_views import SpeechCapabilitiesView, SpeechSynthesizeView, SpeechTranscribeView
from ai.views.ai_speech.voice_stream_views import VoiceChatView, VoiceSentencePollView

urlpatterns = [
    path("api/financial-advisor/ai/speech/capabilities/", feature_required("allows_ai_workspace")(SpeechCapabilitiesView.as_view())),
    path("api/financial-advisor/ai/speech/transcribe/", feature_required("allows_ai_workspace")(SpeechTranscribeView.as_view())),
    path("api/financial-advisor/ai/speech/synthesize/", feature_required("allows_ai_workspace")(SpeechSynthesizeView.as_view())),
    path(
            "api/financial-advisor/ai/chat/",
            feature_required("allows_ai_workspace")(AIChatView.as_view()),
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
            feature_required("allows_ai_workspace")(AIConversationListView.as_view()),
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
            feature_required("allows_ai_workspace")(AIConversationDetailView.as_view()),
        ),
    path(
            "api/financial-advisor/ai/feedback/",
            feature_required("allows_ai_workspace")(AIFeedbackListView.as_view()),
        ),
    path(
            "api/financial-advisor/ai/messages/<int:pk>/export/<str:fmt>/",
            feature_required("allows_ai_workspace")(AIMessageExportView.as_view()),
            name="ai-message-export",
        ),
    path(
            "api/financial-advisor/ai/messages/<int:pk>/feedback/",
            feature_required("allows_ai_workspace")(AIMessageFeedbackView.as_view()),
        ),
    path(
            "api/financial-advisor/ai/progress/",
            feature_required("allows_ai_workspace")(AIProgressView.as_view()),
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
