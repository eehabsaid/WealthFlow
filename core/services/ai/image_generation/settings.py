"""Image generation configuration: AppSettings, app-wide, Settings > AI Advisor (sysadmin).

The same five fields apply wherever WealthFlow runs: enabled, provider, model, endpoint (API URL), api_key. Nothing is derived
from the environment; the provider, model, URL and credentials the sysadmin saved decide how the app connects.
"""

from __future__ import annotations

from core.models import AppSettings
from core.services.ai.credential_encryption import decrypt_credential, encrypt_credential, is_masked, mask_credential

from .providers.registry import get_provider_class

FIELDS = ("enabled", "provider", "model", "endpoint", "api_key", "start_command")
_TRUE = {"true", "1", "yes", "on"}


def _get(field: str, default: str = "") -> str:
    return str(AppSettings.get(f"image_gen_{field}", default, user=None) or default)


def _truth(value) -> bool:
    return str(value or "").strip().lower() in _TRUE


def is_configured(cfg: dict) -> bool:
    """The provider is known and has every value it declares as required (URL and/or credentials)."""
    provider = get_provider_class(cfg.get("provider", ""))
    if provider is None or not str(cfg.get("model") or "").strip():
        return False
    if provider.requires_endpoint and not str(cfg.get("endpoint") or "").strip():
        return False
    return not (provider.requires_api_key and not str(cfg.get("api_key") or "").strip())


def get_image_config(include_secret: bool = False) -> dict:
    raw_key = decrypt_credential(_get("api_key"))
    cfg = {"enabled": _truth(_get("enabled", "false")), "provider": _get("provider").strip().lower(), "model": _get("model").strip(),
           "endpoint": _get("endpoint").strip(), "start_command": _get("start_command").strip(), "api_key": raw_key if include_secret else mask_credential(raw_key)}
    cfg["api_key_is_configured"] = bool(raw_key)
    cfg["is_configured"] = is_configured({**cfg, "api_key": raw_key})
    return cfg


def image_generation_available() -> bool:
    """True only when the switch is on AND the saved settings are complete: the generate_image tool is offered only then."""
    cfg = get_image_config(include_secret=True)
    return cfg["enabled"] and cfg["is_configured"]


def validate_image_settings(data: dict) -> str | None:
    """Error text for a settings POST, or None. Keys missing from `data` keep their saved value."""
    cur = get_image_config(include_secret=True)
    enabled = _truth(data["image_gen_enabled"]) if "image_gen_enabled" in data else cur["enabled"]
    provider = str(data.get("image_gen_provider", cur["provider"]) or "").strip().lower()
    endpoint = str(data.get("image_gen_endpoint", cur["endpoint"]) or "").strip()
    model = str(data.get("image_gen_model", cur["model"]) or "").strip()
    key = str(data.get("image_gen_api_key", "") or "").strip()
    key = cur["api_key"] if (not key or is_masked(key)) else key
    command = str(data.get("image_gen_start_command", cur["start_command"]) or "").strip()
    cls = get_provider_class(provider)
    if command and cls is not None and not cls.supports_managed_server:
        return f"The provider '{provider}' has no server that WealthFlow can start; clear the start command"
    if command and cls is not None:
        from .server import process
        from .server.errors import ServerError
        try:
            args = process.build_args(command, endpoint or "http://127.0.0.1:8188")
            process.check_executable(args)
        except ServerError as exc:
            return str(exc)
    if endpoint and not endpoint.lower().startswith(("http://", "https://")):
        return "Image generation API URL must start with http:// or https://"
    if provider and get_provider_class(provider) is None:
        return f"Unknown image generation provider '{provider}'"
    if enabled and not is_configured({"provider": provider, "model": model, "endpoint": endpoint, "api_key": key}):
        return "Complete the image generation provider settings before enabling it"
    return None


def save_image_settings(data: dict) -> None:
    for field in FIELDS:
        key = f"image_gen_{field}"
        if key not in data:
            continue
        value = data[key]
        if field == "enabled":
            value = "true" if _truth(value) else "false"
        else:
            value = str(value or "").strip()
            if field == "provider":
                value = value.lower()
            if field == "api_key":
                if is_masked(value):
                    continue
                value = encrypt_credential(value) if value else ""
        AppSettings.set(key, value, user=None)
