"""Speech settings payload, validation, and persistence helpers for the AI settings page."""

from core.services.ai.speech import get_speech_config, save_speech_settings
from core.services.ai.speech.settings import FIELDS, KINDS


def build_speech_settings_payload():
    payload = {}
    for kind in KINDS:
        cfg = get_speech_config(kind)
        for field in FIELDS:
            payload[f"speech_{kind}_{field}"] = cfg[field]
        payload[f"speech_{kind}_configured"] = cfg["is_configured"]
        payload[f"speech_{kind}_api_key_is_configured"] = cfg["api_key_is_configured"]
    return payload


def validate_speech_settings_data(data):
    for kind in KINDS:
        enabled = str(data.get(f"speech_{kind}_enabled", "false")).strip().lower() in {"true", "1", "yes", "on"}
        endpoint = str(data.get(f"speech_{kind}_endpoint", "")).strip()
        model = str(data.get(f"speech_{kind}_model", "")).strip()
        if enabled and (not endpoint or not model):
            return f"Configure the {kind.upper()} endpoint and model before enabling it"
        if endpoint and not endpoint.lower().startswith(("http://", "https://")):
            return f"{kind.upper()} endpoint must start with http:// or https://"
        language = str(data.get(f"speech_{kind}_language", "auto")).strip().lower()
        if kind == "stt" and language not in {"auto", "en", "ar", "de", "fr"}:
            return "STT language must be auto, en, ar, de, or fr"
        timeout = data.get(f"speech_{kind}_timeout", 60)
        try:
            if not 1 <= int(timeout) <= 300:
                raise ValueError
        except (ValueError, TypeError):
            return f"{kind.upper()} timeout must be from 1 to 300 seconds"
    return None


def persist_speech_settings(data):
    save_speech_settings(data)
