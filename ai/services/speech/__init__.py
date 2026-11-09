"""Optional, sysadmin-configured speech provider services."""

from ai.services.speech.settings import (
    get_speech_config,
    save_speech_settings,
    speech_runtime_enabled,
)
from ai.services.speech.client import transcribe_audio
from ai.services.speech.tts import synthesize_speech, has_speakable_text, tts_available
from ai.services.speech.diagnostics import test_speech_endpoint

__all__ = ["get_speech_config", "save_speech_settings", "speech_runtime_enabled", "transcribe_audio", "synthesize_speech",
           "has_speakable_text", "tts_available", "test_speech_endpoint"]
