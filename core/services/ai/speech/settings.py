"""Global STT/TTS configuration stored in AppSettings; no speech model is required by default."""

from core.models import AppSettings
from core.services.ai.credential_encryption import encrypt_credential, decrypt_credential, is_masked, mask_credential

KINDS = ("stt", "tts")
FIELDS = ("enabled", "provider", "endpoint", "model", "api_key", "timeout", "voice", "language")


def _get(key, default=""):
    return AppSettings.get(f"speech_{key}", default, user=None)


def _truth(value):
    return str(value or "").strip().lower() in {"true", "1", "yes", "on"}


def get_speech_config(kind, include_secret=False):
    if kind not in KINDS:
        raise ValueError("Unsupported speech kind")
    cfg = {
        "enabled": _truth(_get(f"{kind}_enabled", "false")),
        "provider": _get(f"{kind}_provider"),
        "endpoint": _get(f"{kind}_endpoint"),
        "model": _get(f"{kind}_model"),
        "timeout": _get(f"{kind}_timeout", "60"),
        "voice": _get(f"{kind}_voice"),
        "language": _get(f"{kind}_language", "auto"),
    }
    raw_key = decrypt_credential(_get(f"{kind}_api_key"))
    cfg["api_key"] = raw_key if include_secret else mask_credential(raw_key)
    cfg["is_configured"] = bool(cfg["endpoint"].strip() and cfg["model"].strip())
    cfg["api_key_is_configured"] = bool(raw_key)
    try:
        cfg["timeout"] = max(1, min(300, int(cfg["timeout"])))
    except (TypeError, ValueError):
        cfg["timeout"] = 60
    return cfg


def save_speech_settings(data):
    pending = {}
    for kind in KINDS:
        values = {}
        for field in FIELDS:
            key = f"speech_{kind}_{field}"
            if key not in data:
                continue
            value = data[key]
            if field == "enabled":
                value = "true" if _truth(value) else "false"
            elif field == "language":
                value = str(value or "auto").strip().lower()
                if kind == "stt" and value not in {"auto", "en", "ar", "de", "fr"}:
                    raise ValueError("STT language must be auto, en, ar, de, or fr")
            elif field == "timeout":
                try:
                    value = str(max(1, min(300, int(value))))
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{key} must be an integer from 1 to 300") from exc
            else:
                value = str(value or "").strip()
            if field == "api_key":
                if is_masked(value):
                    continue
                value = encrypt_credential(value) if value else ""
            values[key] = value
        enabled = values.get(f"speech_{kind}_enabled", _get(f"{kind}_enabled", "false")) == "true"
        endpoint = values.get(f"speech_{kind}_endpoint", _get(f"{kind}_endpoint"))
        model = values.get(f"speech_{kind}_model", _get(f"{kind}_model"))
        if enabled and (not endpoint or not model):
            raise ValueError(f"Configure the {kind.upper()} endpoint and model before enabling {kind.upper()}")
        if endpoint and not endpoint.lower().startswith(("http://", "https://")):
            raise ValueError(f"{kind.upper()} endpoint must start with http:// or https://")
        pending.update(values)
    for key, value in pending.items():
        AppSettings.set(key, value, user=None)
