# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    AssetMaintenance,
    FixedAsset,

)
from core.validators import _api_auth_required, _child_owned_object_or_404

@method_decorator(csrf_exempt, name="dispatch")
class AssetMaintenanceListView(View):

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        asset_id = request.GET.get("asset")

        qs = AssetMaintenance.objects.filter(asset__owner=request.user).order_by("-date", "-id")

        if asset_id:
            qs = qs.filter(asset_id=asset_id)

        return JsonResponse({
            "maintenance": [m.to_dict() for m in qs]
        })

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        data = json.loads(request.body)
        get_object_or_404(FixedAsset, pk=data["asset_id"], owner=request.user)

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
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        item = _child_owned_object_or_404(AssetMaintenance, pk, request, parent_field="asset")

        data = json.loads(request.body)

        fields = ["date", "maintenance_type", "cost", "notes"]

        for field in fields:
            if field in data:
                setattr(item, field, data[field])

        item.save()

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        item = _child_owned_object_or_404(AssetMaintenance, pk, request, parent_field="asset")
        item.delete()

        return JsonResponse({"deleted": pk})

