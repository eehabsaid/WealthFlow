# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: part of the settings/market/ domain package. If this file
grows past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

from django.http import JsonResponse
from django.views import View

from core.models import GoldPrice
from core.services.fixed_assets.gold_valuation_service import GoldValuationService


def _gold_for_user(user, latest):
    """Egyptian dealer prices (EGP) for everyone except Gulf-market users, who
    get international-spot prices in their own base currency."""
    from core.services.shared.market_profile import is_gulf_user, spot_gold_snapshot

    data = latest.to_dict()
    if user is not None and getattr(user, "is_authenticated", False) and is_gulf_user(user):
        data.update(spot_gold_snapshot(user, latest))
    return data


class GoldPriceListView(View):
    """GET /api/gold/ → latest gold price"""

    def get(self, request):
        latest = GoldPrice.objects.order_by("-fetched_at", "-id").first()
        if not latest:
            return JsonResponse(
                {"gold": None, "message": "No data yet. Click Refresh."}
            )
        return JsonResponse({"gold": _gold_for_user(request.user, latest)})


class GoldPriceRefreshView(View):
    """Fetches EGP gold prices from goldbullioneg.com and USD/EGP from open.er-api.com."""

    def get(self, request):
        return self.post(request)

    def post(self, request):
        try:
            result = GoldValuationService().refresh_latest_prices().to_dict()
            latest = GoldPrice.objects.order_by("-fetched_at", "-id").first()
            return JsonResponse({**result, "gold": _gold_for_user(request.user, latest) if latest else None})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=502)
