"""Speech API view exports kept separate from the AI chat implementation."""

from ai.views.ai_speech import (
    SpeechCapabilitiesView,
    SpeechTranscribeView,
    SpeechSynthesizeView,
    SpeechSettingsTestView,
)

__all__ = [
    "SpeechCapabilitiesView",
    "SpeechTranscribeView",
    "SpeechSynthesizeView",
    "SpeechSettingsTestView",
]
