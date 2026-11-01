"""Optional, sysadmin-configured speech provider services."""

from .settings import get_speech_config, save_speech_settings, speech_runtime_enabled
from .client import transcribe_audio
from .tts import synthesize_speech, has_speakable_text, tts_available
from .diagnostics import test_speech_endpoint

__all__ = ["get_speech_config", "save_speech_settings", "speech_runtime_enabled", "transcribe_audio", "synthesize_speech",
           "has_speakable_text", "tts_available", "test_speech_endpoint"]
