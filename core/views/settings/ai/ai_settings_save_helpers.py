# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""Validation, persistence, and connection-test helpers for
AISettingsView.post(). Split out purely to keep ai_settings_views.py
under the 200-line file limit. No logic changes.

NOTE: part of the settings/ai/ domain package. If this file grows past
~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

from django.http import JsonResponse

from core.models import AppSettings
from core.services.ai.credential_encryption import encrypt_credential, is_masked
from core.integrations.ai_provider import AVAILABLE_AI_PROVIDERS, get_active_ai_provider


def validate_ai_settings_post_data(data):
    """Returns (validated_dict, error_response). error_response is a
    JsonResponse (400) if validation failed, in which case validated_dict
    is None."""
    provider = str(data.get("ai_provider", "ollama")).strip().lower()
    if provider not in AVAILABLE_AI_PROVIDERS:
        return None, JsonResponse(
            {"error": f"Invalid provider '{provider}'. Must be one of {list(AVAILABLE_AI_PROVIDERS.keys())}"},
            status=400,
        )

    try:
        temperature = float(data.get("ai_temperature", 0.7))
        if not (0.0 <= temperature <= 2.0):
            raise ValueError()
    except (ValueError, TypeError):
        return None, JsonResponse({"error": "ai_temperature must be a float between 0.0 and 2.0"}, status=400)

    try:
        context_size = int(data.get("ai_context_size", 4096))
        if context_size <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return None, JsonResponse({"error": "ai_context_size must be a positive integer"}, status=400)

    try:
        timeout = int(data.get("ai_timeout", 15))
        if timeout <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return None, JsonResponse({"error": "ai_timeout must be a positive integer"}, status=400)

    try:
        max_tokens = int(data.get("ai_max_tokens", 2048))
        if max_tokens <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return None, JsonResponse({"error": "ai_max_tokens must be a positive integer"}, status=400)

    try:
        top_p = float(data.get("ai_top_p", 0.9))
        if not (0.0 <= top_p <= 1.0):
            raise ValueError()
    except (ValueError, TypeError):
        return None, JsonResponse({"error": "ai_top_p must be a float between 0.0 and 1.0"}, status=400)

    try:
        top_k = int(data.get("ai_top_k", 40))
        if top_k <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return None, JsonResponse({"error": "ai_top_k must be a positive integer"}, status=400)

    try:
        repeat_penalty = float(data.get("ai_repeat_penalty", 1.1))
        if repeat_penalty <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return None, JsonResponse({"error": "ai_repeat_penalty must be a positive number"}, status=400)

    try:
        history_window = int(data.get("ai_history_window", 10))
        if history_window <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return None, JsonResponse({"error": "ai_history_window must be a positive integer"}, status=400)

    try:
        context_token_budget = int(data.get("ai_context_token_budget", 2048))
        if context_token_budget <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return None, JsonResponse({"error": "ai_context_token_budget must be a positive integer"}, status=400)

    enabled = bool(data.get("ai_enabled", False))
    read_only = bool(data.get("ai_read_only", True))
    ollama_url = str(data.get("ai_ollama_url", "http://localhost:11434")).strip()
    model = str(data.get("ai_model", "llama3.2:latest")).strip()
    system_prompt = str(data.get("ai_system_prompt", "You are a helpful financial advisor assistant.")).strip()
    seed = str(data.get("ai_seed", "")).strip()
    keep_alive = str(data.get("ai_keep_alive", "5m")).strip()

    validated = {
        "provider": provider,
        "temperature": temperature,
        "context_size": context_size,
        "timeout": timeout,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "top_k": top_k,
        "repeat_penalty": repeat_penalty,
        "history_window": history_window,
        "context_token_budget": context_token_budget,
        "enabled": enabled,
        "read_only": read_only,
        "ollama_url": ollama_url,
        "model": model,
        "system_prompt": system_prompt,
        "seed": seed,
        "keep_alive": keep_alive,
    }
    return validated, None


def persist_ai_settings(data, validated):
    AppSettings.set("ai_enabled", "true" if validated["enabled"] else "false")
    AppSettings.set("ai_read_only", "true" if validated["read_only"] else "false")
    AppSettings.set("ai_provider", validated["provider"])
    AppSettings.set("ai_ollama_url", validated["ollama_url"])
    AppSettings.set("ai_model", validated["model"])
    AppSettings.set("ai_temperature", str(validated["temperature"]))
    AppSettings.set("ai_context_size", str(validated["context_size"]))
    AppSettings.set("ai_timeout", str(validated["timeout"]))
    AppSettings.set("ai_system_prompt", validated["system_prompt"])
    AppSettings.set("ai_max_tokens", str(validated["max_tokens"]))
    AppSettings.set("ai_top_p", str(validated["top_p"]))
    AppSettings.set("ai_top_k", str(validated["top_k"]))
    AppSettings.set("ai_repeat_penalty", str(validated["repeat_penalty"]))
    AppSettings.set("ai_seed", validated["seed"])
    AppSettings.set("ai_keep_alive", validated["keep_alive"])
    AppSettings.set("ai_history_window", str(validated["history_window"]))
    AppSettings.set("ai_context_token_budget", str(validated["context_token_budget"]))

    # Save provider specific non-secret fields
    if "ai_openai_model" in data:
        AppSettings.set("ai_openai_model", str(data["ai_openai_model"] or "").strip())
    if "ai_openai_base_url" in data:
        AppSettings.set("ai_openai_base_url", str(data["ai_openai_base_url"] or "").strip())
    if "ai_claude_model" in data:
        AppSettings.set("ai_claude_model", str(data["ai_claude_model"] or "").strip())
    if "ai_gemini_model" in data:
        AppSettings.set("ai_gemini_model", str(data["ai_gemini_model"] or "").strip())
    if "ai_azure_endpoint" in data:
        AppSettings.set("ai_azure_endpoint", str(data["ai_azure_endpoint"] or "").strip())
    if "ai_azure_deployment" in data:
        AppSettings.set("ai_azure_deployment", str(data["ai_azure_deployment"] or "").strip())
    if "ai_azure_api_version" in data:
        AppSettings.set("ai_azure_api_version", str(data["ai_azure_api_version"] or "").strip())

    # Save secret fields securely with Fernet encryption
    # CRITICAL: If user submits a masked string (starts with '••••'), DO NOT re-encrypt or overwrite!
    secret_keys = ("ai_openai_api_key", "ai_claude_api_key", "ai_gemini_api_key", "ai_azure_api_key")
    for sk in secret_keys:
        if sk in data:
            val = str(data[sk] or "").strip()
            if not val:
                AppSettings.set(sk, "")
            elif is_masked(val):
                # Keep existing stored ciphertext untouched
                pass
            else:
                enc_val = encrypt_credential(val)
                AppSettings.set(sk, enc_val)


def run_ai_settings_connection_test(enabled, model):
    """Run connection test post-save to report connection status."""
    connection_ok = False
    test_error = None
    if enabled:
        active_provider = get_active_ai_provider()
        if active_provider:
            conn_res = active_provider.check_connection()
            m_name = getattr(active_provider, "model", "") or getattr(active_provider, "deployment", "") or model
            model_avail = active_provider.check_model_available(m_name)
            connection_ok = bool(conn_res.get("reachable")) and model_avail
            test_error = conn_res.get("error") if not conn_res.get("reachable") else (None if model_avail else "Model/Deployment not available")
    return connection_ok, test_error
