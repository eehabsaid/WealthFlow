"""Optional, sysadmin-configured speech provider services."""

from .settings import get_speech_config, save_speech_settings
from .client import transcribe_audio, synthesize_speech, test_speech_endpoint

__all__ = ["get_speech_config", "save_speech_settings", "transcribe_audio", "synthesize_speech", "test_speech_endpoint"]
