# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: part of the settings/gold/ domain package. If this file
grows past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404

from core.models import GoldTypeSetting
from core.views.settings.gold.gold_settings_helpers import _seed_gold_settings_defaults


@method_decorator(csrf_exempt, name="dispatch")
class GoldTypeSettingsListView(View):
    def get(self, request):
        _seed_gold_settings_defaults()
        rows = GoldTypeSetting.objects.all()
        return JsonResponse({"items": [row.to_dict() for row in rows]})

    def post(self, request):
        data = json.loads(request.body)
        item = GoldTypeSetting.objects.create(
            name=(data.get("name") or "").strip(),
            is_active=bool(data.get("is_active", True)),
            order=int(data.get("order", 0) or 0),
        )
        return JsonResponse(item.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class GoldTypeSettingsDetailView(View):
    def put(self, request, pk):
        item = get_object_or_404(GoldTypeSetting, pk=pk)
        data = json.loads(request.body)
        for field in ["name", "is_active", "order"]:
            if field in data:
                setattr(item, field, data[field])
        item.save()
        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(GoldTypeSetting, pk=pk)
        item.is_active = False
        item.save(update_fields=["is_active", "updated_at"])
        return JsonResponse({"disabled": pk})
