"""Per-user AI Advisor settings: payload builder and persistence. Only AI_USER_SETTING_KEYS are ever read
or written here; sysadmin-only fields (tier, read-only, multi-agent, URLs, pipeline switches) never appear."""

from core.constants.ai_user_settings import AI_USER_SETTING_KEYS, USE_GENERAL_KEY
from core.integrations.ai_provider import AVAILABLE_AI_PROVIDERS
from core.models import AppSettings
from core.services.ai.ai_defaults import DEFAULT_OLLAMA_MODEL
from core.services.ai.credential_encryption import decrypt_credential, encrypt_credential, is_masked, mask_credential
from core.services.ai.usage import limit_status, uses_general_settings

USER_PROVIDERS = ("ollama", "openai", "claude", "gemini")  # azure/base URLs stay sysadmin-managed
SECRET_KEYS = ("ai_openai_api_key", "ai_claude_api_key", "ai_gemini_api_key")
_DEFAULTS = {
    "ai_enabled": "false", "ai_provider": "ollama", "ai_model": DEFAULT_OLLAMA_MODEL, "ai_temperature": "0.7",
    "ai_context_size": "4096", "ai_timeout": "60", "ai_system_prompt": "You are a helpful financial advisor assistant.",
    "ai_max_tokens": "2048", "ai_top_p": "0.9", "ai_top_k": "40", "ai_repeat_penalty": "1.1", "ai_seed": "",
    "ai_keep_alive": "5m", "ai_history_window": "10", "ai_context_token_budget": "2048",
}


def _own_or_general(user, key, default=""):
    """The user's own row if any, else the general row (shown as the starting point in the form)."""
    own = AppSettings.objects.filter(key=key, owner=user).values_list("value", flat=True).first()
    if own is not None:
        return own
    return AppSettings.get(key, _DEFAULTS.get(key, default))


def build_payload(user):
    fields = {k: _own_or_general(user, k, _DEFAULTS.get(k, "")) for k in sorted(AI_USER_SETTING_KEYS - set(SECRET_KEYS))}
    for key in SECRET_KEYS:  # only the user's OWN key is ever shown (masked); the shared sysadmin key never is
        fields[key] = mask_credential(decrypt_credential(_own_row(user, key)))
    schemas = [c.get_config_schema() for k, c in AVAILABLE_AI_PROVIDERS.items() if k in USER_PROVIDERS]
    return {
        "use_general": uses_general_settings(user),
        "usage": limit_status(user),
        "fields": fields,
        "providers_schema": schemas,
        "effective": {k: AppSettings.get(k, _DEFAULTS.get(k, ""), user=user) for k in ("ai_enabled", "ai_provider", "ai_model")},
    }


def _own_row(user, key):
    return AppSettings.objects.filter(key=key, owner=user).values_list("value", flat=True).first() or ""


def persist_user_ai_settings(user, data, validated):
    """Writes only whitelisted keys for `user`; masked secrets are left untouched."""
    values = {
        "ai_enabled": "true" if validated["enabled"] else "false", "ai_provider": validated["provider"],
        "ai_model": validated["model"], "ai_temperature": str(validated["temperature"]),
        "ai_context_size": str(validated["context_size"]), "ai_timeout": str(validated["timeout"]),
        "ai_system_prompt": validated["system_prompt"], "ai_max_tokens": str(validated["max_tokens"]),
        "ai_top_p": str(validated["top_p"]), "ai_top_k": str(validated["top_k"]),
        "ai_repeat_penalty": str(validated["repeat_penalty"]), "ai_seed": validated["seed"],
        "ai_keep_alive": validated["keep_alive"], "ai_history_window": str(validated["history_window"]),
        "ai_context_token_budget": str(validated["context_token_budget"]),
    }
    for key in ("ai_openai_model", "ai_claude_model", "ai_gemini_model"):
        if key in data:
            values[key] = str(data[key] or "").strip()
    for key, val in values.items():
        assert key in AI_USER_SETTING_KEYS
        AppSettings.set(key, val, user=user)
    for key in SECRET_KEYS:
        if key not in data:
            continue
        raw = str(data[key] or "").strip()
        if not raw:
            AppSettings.set(key, "", user=user)
        elif not is_masked(raw):
            AppSettings.set(key, encrypt_credential(raw), user=user)


def set_use_general(user, use_general):
    AppSettings.set(USE_GENERAL_KEY, "true" if use_general else "false", user=user)
