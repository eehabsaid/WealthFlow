# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""Builds the AISettingsView GET payload. Split out purely to keep
ai_settings_views.py under the 200-line file limit. No logic changes.

NOTE: part of the settings/ai/ domain package. If this file grows past
~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

from core.models import AppSettings
from core.services.ai.ai_defaults import DEFAULT_OLLAMA_MODEL
from core.services.ai.credential_encryption import decrypt_credential, mask_credential
from core.integrations.ai_provider import AVAILABLE_AI_PROVIDERS
from core.views.settings.ai.ai_pipeline_settings import get_pipeline_settings


def build_ai_settings_get_payload(user=None):
    def get(key, default=None):
        return AppSettings.get(key, default, user=user)

    enabled_str = get("ai_enabled", "false").strip().lower()
    enabled = enabled_str in ("true", "1", "yes")

    provider = get("ai_provider", "ollama").strip()
    ollama_url = get("ai_ollama_url", "http://localhost:11434").strip()
    model = get("ai_model", DEFAULT_OLLAMA_MODEL).strip()

    try:
        temperature = float(get("ai_temperature", "0.7"))
    except (ValueError, TypeError):
        temperature = 0.7

    try:
        context_size = int(get("ai_context_size", "4096"))
    except (ValueError, TypeError):
        context_size = 4096

    try:
        timeout = int(get("ai_timeout", "60"))
    except (ValueError, TypeError):
        timeout = 60

    system_prompt = get(
        "ai_system_prompt", "You are a helpful financial advisor assistant."
    ).strip()

    try:
        max_tokens = int(get("ai_max_tokens", "2048"))
    except (ValueError, TypeError):
        max_tokens = 2048

    try:
        top_p = float(get("ai_top_p", "0.9"))
    except (ValueError, TypeError):
        top_p = 0.9

    try:
        top_k = int(get("ai_top_k", "40"))
    except (ValueError, TypeError):
        top_k = 40

    try:
        repeat_penalty = float(get("ai_repeat_penalty", "1.1"))
    except (ValueError, TypeError):
        repeat_penalty = 1.1

    try:
        history_window = int(get("ai_history_window", "10"))
    except (ValueError, TypeError):
        history_window = 10

    try:
        context_token_budget = int(get("ai_context_token_budget", "2048"))
    except (ValueError, TypeError):
        context_token_budget = 2048

    seed = get("ai_seed", "").strip()
    keep_alive = get("ai_keep_alive", "5m").strip()

    read_only_str = get("ai_read_only", "true").strip().lower()
    read_only = read_only_str in ("true", "1", "yes")

    multi_agent_str = get("ai_multi_agent_enabled", "false").strip().lower()
    multi_agent_enabled = multi_agent_str in ("true", "1", "yes")


    # Decrypt secret API keys to generate masked UI display values
    openai_key_dec = decrypt_credential(get("ai_openai_api_key", "").strip())
    claude_key_dec = decrypt_credential(get("ai_claude_api_key", "").strip())
    gemini_key_dec = decrypt_credential(get("ai_gemini_api_key", "").strip())
    azure_key_dec = decrypt_credential(get("ai_azure_api_key", "").strip())

    providers_schema = [
        cls.get_config_schema() for cls in AVAILABLE_AI_PROVIDERS.values()
    ]

    return {
        "ai_enabled": enabled,
        "ai_read_only": read_only,
        "ai_multi_agent_enabled": multi_agent_enabled,
        "ai_provider": provider,
        "ai_ollama_url": ollama_url,
        "ai_model": model,
        "ai_temperature": temperature,
        "ai_context_size": context_size,
        "ai_timeout": timeout,
        "ai_system_prompt": system_prompt,
        "ai_max_tokens": max_tokens,
        "ai_top_p": top_p,
        "ai_top_k": top_k,
        "ai_repeat_penalty": repeat_penalty,
        "ai_seed": seed,
        "ai_keep_alive": keep_alive,
        "ai_history_window": history_window,
        "ai_context_token_budget": context_token_budget,
        # Provider-specific fields
        "ai_openai_api_key": mask_credential(openai_key_dec),
        "ai_openai_is_configured": bool(openai_key_dec),
        "ai_openai_model": get("ai_openai_model", "").strip(),
        "ai_openai_base_url": get("ai_openai_base_url", "https://api.openai.com/v1").strip(),
        "ai_claude_api_key": mask_credential(claude_key_dec),
        "ai_claude_is_configured": bool(claude_key_dec),
        "ai_claude_model": get("ai_claude_model", "").strip(),
        "ai_gemini_api_key": mask_credential(gemini_key_dec),
        "ai_gemini_is_configured": bool(gemini_key_dec),
        "ai_gemini_model": get("ai_gemini_model", "").strip(),
        "ai_azure_api_key": mask_credential(azure_key_dec),
        "ai_azure_is_configured": bool(azure_key_dec),
        "ai_azure_endpoint": get("ai_azure_endpoint", "").strip(),
        "ai_azure_deployment": get("ai_azure_deployment", "").strip(),
        "ai_azure_api_version": get("ai_azure_api_version", "2024-06-01").strip(),
        "providers_schema": providers_schema,
        **get_pipeline_settings(user=user),
    }

