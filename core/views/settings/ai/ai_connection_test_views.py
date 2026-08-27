# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: part of the settings/ai/ domain package. If this file
grows past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.views.auth_views import AdminRequiredMixin
from core.models import AppSettings
from core.services.ai.credential_encryption import decrypt_credential, is_masked
from core.integrations.ai_provider import (
    AVAILABLE_AI_PROVIDERS,
    AzureOpenAIProvider,
    ClaudeProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
)


@method_decorator(csrf_exempt, name="dispatch")
class AIConnectionTestView(AdminRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            data = {}

        provider_key = str(data.get("provider") or AppSettings.get("ai_provider", "ollama")).strip().lower()
        cls = AVAILABLE_AI_PROVIDERS.get(provider_key)
        if not cls:
            return JsonResponse({
                "ok": False,
                "message_key": "ai_provider_invalid",
                "reachable": False,
                "version": None,
                "error": f"Invalid provider '{provider_key}'",
                "response_time_ms": 0,
                "models": [],
                "model_available": False,
            }, status=400)

        # Build test instance using submitted fields or fallback to stored settings
        try:
            timeout = int(data.get("timeout") or AppSettings.get("ai_timeout", "15"))
        except (ValueError, TypeError):
            timeout = 15

        if provider_key == "ollama":
            base_url = str(data.get("base_url") or data.get("ai_ollama_url") or AppSettings.get("ai_ollama_url", "http://localhost:11434")).strip()
            model = str(data.get("model") or data.get("ai_model") or AppSettings.get("ai_model", "llama3.2:latest")).strip()
            provider_inst = OllamaProvider(base_url=base_url, model=model, timeout=timeout)
        elif provider_key == "openai":
            key_raw = str(data.get("api_key") or data.get("ai_openai_api_key") or "").strip()
            key_val = decrypt_credential(AppSettings.get("ai_openai_api_key", "").strip()) if is_masked(key_raw) or not key_raw else key_raw
            model = str(data.get("model") or data.get("ai_openai_model") or AppSettings.get("ai_openai_model", "")).strip()
            base_url = str(data.get("base_url") or data.get("ai_openai_base_url") or AppSettings.get("ai_openai_base_url", "https://api.openai.com/v1")).strip()
            provider_inst = OpenAIProvider(api_key=key_val, model=model, base_url=base_url, timeout=timeout)
        elif provider_key == "claude":
            key_raw = str(data.get("api_key") or data.get("ai_claude_api_key") or "").strip()
            key_val = decrypt_credential(AppSettings.get("ai_claude_api_key", "").strip()) if is_masked(key_raw) or not key_raw else key_raw
            model = str(data.get("model") or data.get("ai_claude_model") or AppSettings.get("ai_claude_model", "")).strip()
            provider_inst = ClaudeProvider(api_key=key_val, model=model, timeout=timeout)
        elif provider_key == "gemini":
            key_raw = str(data.get("api_key") or data.get("ai_gemini_api_key") or "").strip()
            key_val = decrypt_credential(AppSettings.get("ai_gemini_api_key", "").strip()) if is_masked(key_raw) or not key_raw else key_raw
            model = str(data.get("model") or data.get("ai_gemini_model") or AppSettings.get("ai_gemini_model", "")).strip()
            provider_inst = GeminiProvider(api_key=key_val, model=model, timeout=timeout)
        elif provider_key == "azure":
            key_raw = str(data.get("api_key") or data.get("ai_azure_api_key") or "").strip()
            key_val = decrypt_credential(AppSettings.get("ai_azure_api_key", "").strip()) if is_masked(key_raw) or not key_raw else key_raw
            endpoint = str(data.get("endpoint") or data.get("ai_azure_endpoint") or AppSettings.get("ai_azure_endpoint", "")).strip()
            deployment = str(data.get("deployment") or data.get("ai_azure_deployment") or AppSettings.get("ai_azure_deployment", "")).strip()
            api_version = str(data.get("api_version") or data.get("ai_azure_api_version") or AppSettings.get("ai_azure_api_version", "2024-06-01")).strip()
            provider_inst = AzureOpenAIProvider(api_key=key_val, endpoint=endpoint, deployment=deployment, api_version=api_version, timeout=timeout)
            model = deployment
        else:
            provider_inst = cls.from_settings()
            model = str(data.get("model") or "").strip()

        conn_res = provider_inst.check_connection() if provider_inst else {"reachable": False, "error": "Provider init failed"}
        models = provider_inst.list_models() if provider_inst else []
        target_model = model or getattr(provider_inst, "model", "") or getattr(provider_inst, "deployment", "")
        model_avail = provider_inst.check_model_available(target_model) if provider_inst else False

        reachable = bool(conn_res.get("reachable"))
        ok = reachable and model_avail

        return JsonResponse({
            "ok": ok,
            "message_key": "ai_connection_success" if ok else "ai_connection_failed",
            "reachable": reachable,
            "version": conn_res.get("version"),
            "error": conn_res.get("error"),
            "response_time_ms": conn_res.get("response_time_ms", 0),
            "models": models,
            "model_available": model_avail,
        }, status=200 if ok else 400)
