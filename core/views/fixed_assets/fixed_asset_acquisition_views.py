# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import AssetAcquisitionCost

@method_decorator(csrf_exempt, name="dispatch")
class AssetAcquisitionCostListView(View):
    def get(self, request):
        asset_id = request.GET.get("asset")
        qs = AssetAcquisitionCost.objects.all().order_by("date", "id")
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        return JsonResponse({
            "acquisition_costs": [r.to_dict() for r in qs]
        })

    def post(self, request):
        data = json.loads(request.body)
        item = AssetAcquisitionCost.objects.create(
            asset_id=data["asset_id"],
            date=data.get("date") or None,
            category=data["category"],
            description=data.get("description", ""),
            amount_egp=data.get("amount_egp") or 0,
            usd_rate=data.get("usd_rate") or 0,
            amount_usd=data.get("amount_usd") or 0,
            notes=data.get("notes", ""),
        )
        return JsonResponse(item.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class AssetAcquisitionCostDetailView(View):
    def put(self, request, pk):
        item = get_object_or_404(AssetAcquisitionCost, pk=pk)
        data = json.loads(request.body)
        fields = [
            "date",
            "category",
            "description",
            "amount_egp",
            "usd_rate",
            "amount_usd",
            "notes",
        ]
        for field in fields:
            if field in data:
                val = data[field]
                if field == "date" and not val:
                    val = None
                elif field in ["amount_egp", "amount_usd", "usd_rate"]:
                    val = val or 0
                setattr(item, field, val)
        item.save()
        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(AssetAcquisitionCost, pk=pk)
        item.delete()
        return JsonResponse({"deleted": pk})

@method_decorator(csrf_exempt, name="dispatch")
class AssetAcquisitionCostCategoriesView(View):
    def get(self, request):
        from core.constants import ACQUISITION_COST_CATEGORIES
        return JsonResponse({"categories": ACQUISITION_COST_CATEGORIES})
