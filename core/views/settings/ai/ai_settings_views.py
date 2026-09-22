# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: part of the settings/ai/ domain package. If this file
grows past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

import json
from django.http import JsonResponse
from django.views import View

from core.validators.json_body import parse_json_body
from core.views.auth_views import AdminRequiredMixin
from core.views.settings.ai.ai_settings_get_helpers import build_ai_settings_get_payload
from core.views.settings.ai.ai_settings_save_helpers import (
    validate_ai_settings_post_data,
    persist_ai_settings,
    run_ai_settings_connection_test,
)

# ══════════════════════════════════════════════════════════════
# AI ADVISOR SETTINGS VIEW — single app-wide configuration
# (owner=NULL rows only; sysadmin-only, see SYSADMIN_ONLY_SETTINGS_TABS)
# ══════════════════════════════════════════════════════════════


class AISettingsView(AdminRequiredMixin, View):
    def get(self, request):
        return JsonResponse(build_ai_settings_get_payload(user=None))

    def post(self, request):
        try:
            data = parse_json_body(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        validated, error_response = validate_ai_settings_post_data(data)
        if error_response:
            return error_response

        persist_ai_settings(data, validated, user=None)
        connection_ok, test_error = run_ai_settings_connection_test(
            validated["enabled"], validated["model"], user=None
        )
        message_key = "ai_save_success" if (not validated["enabled"] or connection_ok) else "ai_save_success_test_failed"

        return JsonResponse({
            "ok": True,
            "connection_ok": connection_ok,
            "message_key": message_key,
            "test_error": test_error,
        })
