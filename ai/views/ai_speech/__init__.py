"""Speech feature API views."""

from ai.views.ai_speech.speech_views import (
    SpeechCapabilitiesView,
    SpeechTranscribeView,
    SpeechSynthesizeView,
)
from ai.views.ai_speech.speech_settings_views import SpeechSettingsTestView

__all__ = ["SpeechCapabilitiesView", "SpeechTranscribeView", "SpeechSynthesizeView", "SpeechSettingsTestView"]
