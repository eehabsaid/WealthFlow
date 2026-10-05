"""GET/POST /api/settings/ai/me/ — the signed-in user's own AI Advisor settings (any authenticated user)."""

import json

from django.http import JsonResponse
from django.views import View

from core.validators.json_body import parse_json_body
from core.views.settings.ai.ai_settings_save_helpers import run_ai_settings_connection_test, validate_ai_settings_post_data
from core.views.settings.ai.ai_user_settings_helpers import (
    USER_PROVIDERS, build_payload, persist_user_ai_settings, set_use_general,
)


class AIUserSettingsView(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return JsonResponse(build_payload(request.user))

    def post(self, request):
        try:
            data = parse_json_body(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        if bool(data.get("use_general", True)):
            set_use_general(request.user, True)
            return JsonResponse({"ok": True, "use_general": True, "usage": build_payload(request.user)["usage"]})

        # Tier / read-only are never taken from a user: validate against the neutral read tier only.
        checked = {k: v for k, v in data.items() if k not in ("ai_permission_tier", "ai_read_only")}
        checked["ai_permission_tier"] = "read"
        if str(checked.get("ai_provider", "ollama")).strip().lower() not in USER_PROVIDERS:
            return JsonResponse({"error": f"Invalid provider. Must be one of {list(USER_PROVIDERS)}"}, status=400)
        validated, error_response = validate_ai_settings_post_data(checked)
        if error_response:
            return error_response

        persist_user_ai_settings(request.user, data, validated)
        set_use_general(request.user, False)
        ok, err = run_ai_settings_connection_test(validated["enabled"], validated["model"], user=request.user)
        return JsonResponse({
            "ok": True, "use_general": False, "connection_ok": ok, "test_error": err,
            "message_key": "ai_save_success" if (not validated["enabled"] or ok) else "ai_save_success_test_failed",
        })
