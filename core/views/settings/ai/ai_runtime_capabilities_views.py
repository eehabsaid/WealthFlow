# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: part of the settings/ai/ domain package. If this file
grows past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly.

Read-only inspection endpoint (item 8/9 of the AI-agent-architecture
backlog): detects local hardware, queries Ollama for the configured
model's real capabilities and what's currently loaded, runs a small live
timing benchmark, and returns a recommended ai_context_size/ai_max_tokens/
ai_timeout/ai_keep_alive. Applying a recommendation is just a normal
POST to the existing AISettingsView — this view never persists anything.
"""

from django.http import JsonResponse
from django.views import View

from core.models import AppSettings
from core.services.ai.ai_defaults import DEFAULT_OLLAMA_MODEL
from core.services.ai.runtime_capabilities import inspect_and_recommend
from core.views.auth_views import AdminRequiredMixin


class AIRuntimeCapabilitiesView(AdminRequiredMixin, View):
    def get(self, request):
        base_url = AppSettings.get("ai_ollama_url", "http://localhost:11434").strip()
        model = AppSettings.get("ai_model", DEFAULT_OLLAMA_MODEL).strip()

        try:
            current = {
                "ai_context_size": int(AppSettings.get("ai_context_size", "4096")),
                "ai_max_tokens": int(AppSettings.get("ai_max_tokens", "1024")),
                "ai_timeout": int(AppSettings.get("ai_timeout", "60")),
            }
        except (ValueError, TypeError):
            current = {"ai_context_size": 4096, "ai_max_tokens": 1024, "ai_timeout": 60}
        current["ai_keep_alive"] = AppSettings.get("ai_keep_alive", "5m").strip()

        try:
            timeout = int(AppSettings.get("ai_timeout", "60"))
        except (ValueError, TypeError):
            timeout = 60

        report = inspect_and_recommend(base_url=base_url, model=model, current=current, timeout=max(timeout, 30))
        return JsonResponse(report)
