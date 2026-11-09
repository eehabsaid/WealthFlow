"""AI settings routes (Settings > AI Advisor, speech and image tests)."""

from django.urls import path

from ai.views.ai_speech.speech_settings_views import SpeechSettingsTestView, SpeechVoiceSampleView
from ai.views.settings.ai_connection_test_views import AIConnectionTestView
from ai.views.settings.ai_image_test_view import ImageSettingsTestView
from ai.views.settings.ai_provider_views import AIProviderListView
from ai.views.settings.ai_runtime_capabilities_views import AIRuntimeCapabilitiesView
from ai.views.settings.ai_settings_views import AISettingsView
from ai.views.settings.ai_user_limits_views import AIUserLimitsView
from ai.views.settings.ai_user_settings_views import AIUserSettingsView

urlpatterns = [
    path("api/settings/ai/", AISettingsView.as_view()),
    path("api/settings/ai/me/", AIUserSettingsView.as_view()),
    path("api/settings/ai/user-limits/", AIUserLimitsView.as_view()),
    path("api/settings/ai/providers/", AIProviderListView.as_view()),
    path("api/settings/ai/test-connection/", AIConnectionTestView.as_view()),
    path("api/settings/ai/runtime-capabilities/", AIRuntimeCapabilitiesView.as_view()),
    path("api/settings/ai/speech/test/", SpeechSettingsTestView.as_view()),
    path("api/settings/ai/speech/voice-sample/", SpeechVoiceSampleView.as_view()),
    path("api/settings/ai/image-generation/test/", ImageSettingsTestView.as_view()),
]
