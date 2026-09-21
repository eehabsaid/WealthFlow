# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""Paymob payment-gateway settings — admin-configured entirely from the UI
(Settings > Billing Plans tab), never hardcoded. Reuses the same
AppSettings + Fernet-encryption pattern already used for AI provider keys.

NOTE: part of the settings/billing/ domain package. If this file grows
past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

import json

from django.http import JsonResponse
from django.views import View

from core.validators.json_body import parse_json_body
from core.models import AppSettings
from core.views.auth_views import AdminRequiredMixin
from core.services.ai.credential_encryption import (
    decrypt_credential,
    encrypt_credential,
    is_masked,
    mask_credential,
)

# Non-secret fields, stored as plain text in AppSettings.
_PLAIN_KEYS = ("paymob_integration_id", "paymob_iframe_id")
# Secret fields, stored Fernet-encrypted (same convention as AI keys).
_SECRET_KEYS = ("paymob_api_key", "paymob_hmac_secret")


def _is_paymob_configured() -> bool:
    """True once every field Paymob checkout/webhook needs is filled in.
    While False, checkout runs in fake/test mode instead."""
    if not AppSettings.get("paymob_integration_id", "").strip():
        return False
    if not AppSettings.get("paymob_iframe_id", "").strip():
        return False
    if not decrypt_credential(AppSettings.get("paymob_api_key", "").strip()):
        return False
    if not decrypt_credential(AppSettings.get("paymob_hmac_secret", "").strip()):
        return False
    return True


def _build_get_payload():
    api_key_dec = decrypt_credential(AppSettings.get("paymob_api_key", "").strip())
    hmac_dec = decrypt_credential(AppSettings.get("paymob_hmac_secret", "").strip())
    return {
        "paymob_api_key": mask_credential(api_key_dec),
        "paymob_hmac_secret": mask_credential(hmac_dec),
        "paymob_integration_id": AppSettings.get("paymob_integration_id", "").strip(),
        "paymob_iframe_id": AppSettings.get("paymob_iframe_id", "").strip(),
        "is_configured": _is_paymob_configured(),
    }


class PaymobGatewaySettingsView(AdminRequiredMixin, View):
    def get(self, request):
        return JsonResponse(_build_get_payload())

    def post(self, request):
        try:
            data = parse_json_body(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        for key in _PLAIN_KEYS:
            if key in data:
                AppSettings.set(key, str(data[key] or "").strip())

        for key in _SECRET_KEYS:
            if key not in data:
                continue
            val = str(data[key] or "").strip()
            if not val:
                AppSettings.set(key, "")
            elif is_masked(val):
                # Masked placeholder resubmitted unchanged — keep existing ciphertext.
                pass
            else:
                AppSettings.set(key, encrypt_credential(val))

        return JsonResponse({"ok": True, "is_configured": _is_paymob_configured()})
