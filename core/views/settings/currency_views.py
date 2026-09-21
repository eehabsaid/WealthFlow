# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: single-resource file. If it grows past ~200 lines, split it and
move the resulting files into a settings/<domain>/ subfolder (see
settings/ai/ or settings/gold/ for the pattern: an empty __init__.py plus
one file per concern), then update core/views/settings/__init__.py.

Per-user catalog: every user gets their own editable copy of the
Currency list (seeded from the platform template at signup — see
core/authentication/views/signals.py). Always scope by owner=request.user
here. NEVER use these views/queries for billing/Plan currency lookups —
those must stay against the owner=None platform template (see
core/views/billing_views.py)."""


from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404

from core.validators.json_body import parse_json_body
from core.models import Currency


class CurrencyListView(View):
    def get(self, request):
        currencies = Currency.objects.filter(owner=request.user).order_by("order")
        return JsonResponse({"currencies": [c.to_dict() for c in currencies]})

    def post(self, request):
        data = parse_json_body(request)
        currency = Currency.objects.create(
            owner=request.user,
            code=data["code"],
            symbol=data.get("symbol", ""),
            flag=data.get("flag", "💱"),
            name=data.get("name", data["code"]),
            order=data.get("order", 0),
        )
        return JsonResponse(currency.to_dict(), status=201)


class CurrencyDetailView(View):
    def get(self, request, pk):
        c = get_object_or_404(Currency, pk=pk, owner=request.user)
        return JsonResponse(c.to_dict())

    def put(self, request, pk):
        c = get_object_or_404(Currency, pk=pk, owner=request.user)
        data = parse_json_body(request)
        for field in ["code", "symbol", "flag", "name", "order"]:
            if field in data:
                setattr(c, field, data[field])
        c.save()
        return JsonResponse(c.to_dict())

    def delete(self, request, pk):
        c = get_object_or_404(Currency, pk=pk, owner=request.user)
        c.delete()
        return JsonResponse({"deleted": pk})
