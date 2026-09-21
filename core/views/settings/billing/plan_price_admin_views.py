# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: part of the settings/billing/ domain package. If this file
grows past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404

from core.validators.json_body import parse_json_body
from core.models import Currency, Plan, PlanPrice
from core.views.auth_views import AdminRequiredMixin


class PlanPriceAdminListView(AdminRequiredMixin, View):
    """Prices for one plan. `currency` in the POST body must be the id of an
    app-configured Currency (Settings > Currency) — never a raw code string,
    so this can never introduce a currency the app doesn't already support."""

    def get(self, request, plan_id):
        plan = get_object_or_404(Plan, pk=plan_id)
        prices = plan.prices.select_related("currency").all()
        return JsonResponse({"prices": [p.to_dict() for p in prices]})

    def post(self, request, plan_id):
        plan = get_object_or_404(Plan, pk=plan_id)
        data = parse_json_body(request)
        currency = get_object_or_404(Currency, pk=data.get("currency"))
        if PlanPrice.objects.filter(plan=plan, currency=currency).exists():
            return JsonResponse(
                {"error": f"{plan.name} already has a price in {currency.code}."}, status=400
            )
        price = PlanPrice.objects.create(plan=plan, currency=currency, amount=data.get("amount", 0))
        return JsonResponse(price.to_dict(), status=201)


class PlanPriceAdminDetailView(AdminRequiredMixin, View):
    def put(self, request, plan_id, price_id):
        price = get_object_or_404(PlanPrice, pk=price_id, plan_id=plan_id)
        data = parse_json_body(request)
        if "amount" in data:
            price.amount = data["amount"]
        price.save()
        return JsonResponse(price.to_dict())

    def delete(self, request, plan_id, price_id):
        price = get_object_or_404(PlanPrice, pk=price_id, plan_id=plan_id)
        price.delete()
        return JsonResponse({"deleted": price_id})
