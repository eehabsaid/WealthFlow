# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false

"""GET /api/fixed-assets/usd-rate/?currency_id=<id>

Shared by the "Now" button on the Fixed Asset General, Renovation,
Acquisition Cost and Furniture tabs. Logic lives entirely in
UsdRateService - this view is a thin HTTP wrapper only.
"""

from django.http import JsonResponse
from django.views import View

from core.services.fixed_assets.usd_rate_service import UsdRateService, UsdRateError


class FixedAssetUsdRateView(View):
    def get(self, request):
        currency_id = request.GET.get("currency_id")
        if not currency_id:
            return JsonResponse({"error": "currency_id is required"}, status=400)

        try:
            result = UsdRateService().get_rate_for_currency(currency_id, owner=request.user)
            return JsonResponse(result.to_dict())
        except UsdRateError as e:
            return JsonResponse({"error": str(e)}, status=502)
