"""Settings > Billing: Stripe credentials (admin-only). Secrets are Fernet-encrypted like the Paymob and AI keys
and only ever returned masked; a masked value posted back unchanged keeps the stored secret."""

import json
import re

from django.http import JsonResponse
from django.views import View

from core.models import AppSettings
from core.services.ai.credential_encryption import encrypt_credential, is_masked, mask_credential
from core.services.billing.stripe_gateway import DEFAULT_CURRENCIES, StripeGateway
from core.validators.json_body import parse_json_body
from core.views.auth_views import AdminRequiredMixin

_SECRET_KEYS = ("stripe_secret_key", "stripe_webhook_secret")
_CODE_RE = re.compile(r"^[A-Z]{3}$")
WEBHOOK_PATH = "/api/billing/stripe/webhook/"


def _payload() -> dict:
    cfg = StripeGateway.get_config()
    return {
        "stripe_secret_key": mask_credential(cfg["secret_key"]),
        "stripe_webhook_secret": mask_credential(cfg["webhook_secret"]),
        "stripe_currencies": ",".join(StripeGateway.currencies()) or DEFAULT_CURRENCIES,
        "is_configured": StripeGateway.is_configured(),
        "webhook_path": WEBHOOK_PATH,
    }


class StripeGatewaySettingsView(AdminRequiredMixin, View):
    def get(self, request):
        return JsonResponse(_payload())

    def post(self, request):
        try:
            data = parse_json_body(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)
        if "stripe_currencies" in data:
            codes = [c.strip().upper() for c in str(data["stripe_currencies"] or "").replace(";", ",").split(",") if c.strip()]
            if not codes or not all(_CODE_RE.match(c) for c in codes):
                return JsonResponse({"error": "Invalid currencies"}, status=400)
            AppSettings.set("stripe_currencies", ",".join(dict.fromkeys(codes)))
        for key in _SECRET_KEYS:
            if key not in data:
                continue
            val = str(data[key] or "").strip()
            if not val:
                AppSettings.set(key, "")
            elif not is_masked(val):
                AppSettings.set(key, encrypt_credential(val))
        return JsonResponse({"ok": True, **_payload()})
