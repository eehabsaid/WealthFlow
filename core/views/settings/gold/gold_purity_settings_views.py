# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: part of the settings/gold/ domain package. If this file
grows past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

import json
from decimal import Decimal
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404

from core.models import GoldPuritySetting
from core.views.settings.gold.gold_settings_helpers import _seed_gold_settings_defaults


@method_decorator(csrf_exempt, name="dispatch")
class GoldPuritySettingsListView(View):
    def get(self, request):
        _seed_gold_settings_defaults()
        rows = GoldPuritySetting.objects.all()
        return JsonResponse({"items": [row.to_dict() for row in rows]})

    def post(self, request):
        data = json.loads(request.body)
        key = str(data.get("key") or "").strip().lower()
        if key and not key.endswith("k"):
            key = f"{key}k"
        item = GoldPuritySetting.objects.create(
            key=key,
            label=(data.get("label") or "").strip() or key.upper(),
            cashback_per_gram=Decimal(str(data.get("cashback_per_gram", 0) or 0)),
            is_active=bool(data.get("is_active", True)),
            order=int(data.get("order", 0) or 0),
        )
        return JsonResponse(item.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class GoldPuritySettingsDetailView(View):
    def put(self, request, pk):
        item = get_object_or_404(GoldPuritySetting, pk=pk)
        data = json.loads(request.body)

        if "key" in data:
            key = str(data.get("key") or "").strip().lower()
            if key and not key.endswith("k"):
                key = f"{key}k"
            item.key = key

        if "label" in data:
            item.label = (data.get("label") or "").strip()

        if "cashback_per_gram" in data:
            item.cashback_per_gram = Decimal(str(data.get("cashback_per_gram") or 0))

        if "is_active" in data:
            item.is_active = bool(data.get("is_active"))

        if "order" in data:
            item.order = int(data.get("order") or 0)

        item.save()
        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(GoldPuritySetting, pk=pk)
        item.is_active = False
        item.save(update_fields=["is_active", "updated_at"])
        return JsonResponse({"disabled": pk})
