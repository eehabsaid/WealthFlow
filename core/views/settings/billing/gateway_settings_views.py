# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""Paymob payment-gateway settings — admin-configured entirely from the UI
(Settings > Billing Plans tab), never hardcoded. Reuses the same
AppSettings + Fernet-encryption pattern already used for AI provider keys.

NOTE: part of the settings/billing/ domain package. If this file grows
past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

import json
import re
from urllib.parse import urlparse

from django.http import JsonResponse
from django.views import View

from core.validators.json_body import parse_json_body
from core.models import AppSettings
from core.views.auth_views import AdminRequiredMixin
from core.services.billing.paymob_gateway import (
    PaymobGateway,
    normalize_base_url,
    region_key,
)
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


# Currencies whose own regional Paymob account the Settings card manages.
_REGION_CODES = ("SAR", "AED")
_REGION_PLAIN = ("integration_id", "iframe_id", "base_url")
_REGION_SECRET = ("api_key", "hmac_secret")
_CODE_RE = re.compile(r"^[A-Z]{3}$")


def _valid_paymob_host(value: str) -> bool:
    """Admin-supplied host must be a Paymob domain (no arbitrary outbound targets)."""
    if not str(value or "").strip():
        return True
    host = (urlparse(normalize_base_url(value)).hostname or "").lower()
    return host == "paymob.com" or host.endswith(".paymob.com")


def _regions_payload() -> dict:
    out = {}
    for code in _REGION_CODES:
        cfg = PaymobGateway.get_region_config(code) or {}
        out[code] = {
            "api_key": mask_credential(cfg.get("api_key", "")),
            "hmac_secret": mask_credential(cfg.get("hmac_secret", "")),
            "integration_id": cfg.get("integration_id", ""),
            "iframe_id": cfg.get("iframe_id", ""),
            "base_url": AppSettings.get(region_key(code, "base_url"), "").strip(),
            "is_configured": PaymobGateway.is_configured(code) and PaymobGateway.get_region_config(code) is not None,
        }
    return out


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
        "paymob_default_currencies": ",".join(PaymobGateway.default_currencies()),
        "regions": _regions_payload(),
    }


class PaymobGatewaySettingsView(AdminRequiredMixin, View):
    def get(self, request):
        return JsonResponse(_build_get_payload())

    def post(self, request):
        try:
            data = parse_json_body(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        regions = data.get("regions") or {}
        if not isinstance(regions, dict):
            return JsonResponse({"error": "Invalid regions"}, status=400)
        for code, fields in regions.items():
            code = str(code).strip().upper()
            if not _CODE_RE.match(code) or not isinstance(fields, dict):
                return JsonResponse({"error": "Invalid region currency"}, status=400)
            if not _valid_paymob_host(fields.get("base_url", "")):
                return JsonResponse({"error": "Base URL must be a paymob.com address"}, status=400)
        if "paymob_default_currencies" in data:
            codes = [c.strip().upper() for c in str(data["paymob_default_currencies"] or "").replace(";", ",").split(",") if c.strip()]
            if not codes or not all(_CODE_RE.match(c) for c in codes):
                return JsonResponse({"error": "Invalid default currencies"}, status=400)
            AppSettings.set("paymob_default_currencies", ",".join(dict.fromkeys(codes)))
        for code, fields in regions.items():
            code = str(code).strip().upper()
            for field in _REGION_PLAIN:
                if field in fields:
                    AppSettings.set(region_key(code, field), str(fields[field] or "").strip())
            for field in _REGION_SECRET:
                if field not in fields:
                    continue
                val = str(fields[field] or "").strip()
                if not val:
                    AppSettings.set(region_key(code, field), "")
                elif not is_masked(val):
                    AppSettings.set(region_key(code, field), encrypt_credential(val))

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

        return JsonResponse({"ok": True, "is_configured": _is_paymob_configured(), "regions": _regions_payload()})
