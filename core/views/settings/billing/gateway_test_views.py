"""Settings > Billing: 'Test connection' for a regional (SAR / AED) Paymob account. Authenticates only: no order, no charge."""

import json

from django.http import JsonResponse
from django.views import View

from core.services.billing.paymob_gateway import PaymobGateway
from core.validators.json_body import parse_json_body
from core.views.auth_views import AdminRequiredMixin

_REGION_CODES = ("SAR", "AED")


class PaymobGatewayTestView(AdminRequiredMixin, View):
    """POST {currency: "SAR"|"AED"}: tests the SAVED credentials of that region (save first)."""

    def post(self, request):
        try:
            data = parse_json_body(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)
        code = str(data.get("currency", "")).strip().upper()
        if code not in _REGION_CODES:
            return JsonResponse({"error": "Invalid region currency"}, status=400)
        return JsonResponse(PaymobGateway.test_connection(code))
