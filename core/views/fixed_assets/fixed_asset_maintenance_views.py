# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    AssetMaintenance,

)

@method_decorator(csrf_exempt, name="dispatch")
class AssetMaintenanceListView(View):

    def get(self, request):
        asset_id = request.GET.get("asset")

        qs = AssetMaintenance.objects.all().order_by("date", "id")

        if asset_id:
            qs = qs.filter(asset_id=asset_id)

        return JsonResponse({
            "maintenance": [m.to_dict() for m in qs]
        })

    def post(self, request):
        data = json.loads(request.body)

        item = AssetMaintenance.objects.create(
            asset_id=data["asset_id"],
            date=data["date"],
            maintenance_type=data["maintenance_type"],
            cost=data.get("cost", 0),
            notes=data.get("notes", ""),
        )

        return JsonResponse(item.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class AssetMaintenanceDetailView(View):

    def put(self, request, pk):
        item = get_object_or_404(AssetMaintenance, pk=pk)

        data = json.loads(request.body)

        fields = ["date", "maintenance_type", "cost", "notes"]

        for field in fields:
            if field in data:
                setattr(item, field, data[field])

        item.save()

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(AssetMaintenance, pk=pk)
        item.delete()

        return JsonResponse({"deleted": pk})

