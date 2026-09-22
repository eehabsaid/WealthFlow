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
from core.services.shared.base_currency import (
    can_be_default, get_user_base_code, get_user_base_info, set_user_base_currency,
)

_BASE_ERROR_KEYS = {
    "invalid_currency": "currency_default_invalid",
    "multi_currency_disabled": "currency_default_unavailable",
    "no_rate_for_currency": "currency_default_no_rate",
    "exchange_rate_missing": "currency_default_no_rate",
}


class CurrencyListView(View):
    def get(self, request):
        currencies = Currency.objects.filter(owner=request.user).order_by("order")
        default_code = get_user_base_code(request.user)
        rows = [
            {**c.to_dict(), "is_default": c.code.upper() == default_code, "can_be_default": can_be_default(c.code)}
            for c in currencies
        ]
        return JsonResponse({"currencies": rows, "default_code": default_code})

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
        is_default = c.code.upper() == get_user_base_code(request.user)
        if is_default and str(data.get("code", c.code)).upper() != c.code.upper():
            return _default_locked()
        for field in ["code", "symbol", "flag", "name", "order"]:
            if field in data:
                setattr(c, field, data[field])
        c.save()
        return JsonResponse(c.to_dict())

    def delete(self, request, pk):
        c = get_object_or_404(Currency, pk=pk, owner=request.user)
        if c.code.upper() == get_user_base_code(request.user):
            return _default_locked()
        c.delete()
        return JsonResponse({"deleted": pk})


def _default_locked():
    return JsonResponse(
        {"error": "The default currency cannot be renamed or deleted.", "error_key": "currency_default_locked"},
        status=409,
    )


class BaseCurrencyView(View):
    """GET: the user's default currency. POST {code}: change it."""

    def get(self, request):
        return JsonResponse(get_user_base_info(request.user))

    def post(self, request):
        data = parse_json_body(request)
        try:
            set_user_base_currency(request.user, data.get("code"))
        except ValueError as exc:
            key = _BASE_ERROR_KEYS.get(str(exc), "currency_default_invalid")
            return JsonResponse({"error": str(exc), "error_key": key}, status=400)
        return JsonResponse(get_user_base_info(request.user))
