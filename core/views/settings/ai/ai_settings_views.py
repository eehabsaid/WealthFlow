# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: part of the settings/ai/ domain package. If this file
grows past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

import json
from django.http import JsonResponse
from django.views import View

from core.validators.json_body import parse_json_body
from core.views.auth_views import PermissionRequiredMixin
from core.views.settings.ai.ai_settings_get_helpers import build_ai_settings_get_payload
from core.views.settings.ai.ai_settings_save_helpers import (
    validate_ai_settings_post_data,
    persist_ai_settings,
    run_ai_settings_connection_test,
)

# ══════════════════════════════════════════════════════════════
# AI ADVISOR SETTINGS VIEW (Phase 1 Infrastructure)
# ══════════════════════════════════════════════════════════════


class AISettingsView(PermissionRequiredMixin, View):
    required_key = "settings_aiadvisor"
    def get(self, request):
        return JsonResponse(build_ai_settings_get_payload(user=request.user))

    def post(self, request):
        try:
            data = parse_json_body(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        validated, error_response = validate_ai_settings_post_data(data)
        if error_response:
            return error_response

        persist_ai_settings(data, validated, user=request.user)
        connection_ok, test_error = run_ai_settings_connection_test(
            validated["enabled"], validated["model"], user=request.user
        )
        message_key = "ai_save_success" if (not validated["enabled"] or connection_ok) else "ai_save_success_test_failed"

        return JsonResponse({
            "ok": True,
            "connection_ok": connection_ok,
            "message_key": message_key,
            "test_error": test_error,
        })
