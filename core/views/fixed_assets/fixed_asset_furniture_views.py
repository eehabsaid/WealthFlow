# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    AssetFurniture,

)

@method_decorator(csrf_exempt, name="dispatch")
class AssetFurnitureListView(View):

    def get(self, request):
        asset_id = request.GET.get("asset")

        qs = AssetFurniture.objects.all().order_by("name")

        if asset_id:
            qs = qs.filter(asset_id=asset_id)

        return JsonResponse({
            "furniture": [f.to_dict() for f in qs]
        })

    def post(self, request):
        data = json.loads(request.body)

        item = AssetFurniture.objects.create(
            asset_id=data["asset_id"],
            name=data["name"],
            category=data.get("category", ""),
            purchase_date=data.get("purchase_date") or None,
            amount_egp=data.get("amount_egp", 0),
            usd_rate=data.get("usd_rate", 0),
            amount_usd=data.get("amount_usd", 0),
            quantity=data.get("quantity", 1),
            notes=data.get("notes", ""),
        )

        return JsonResponse(item.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class AssetFurnitureDetailView(View):

    def put(self, request, pk):
        item = get_object_or_404(AssetFurniture, pk=pk)

        data = json.loads(request.body)

        fields = [
            "name",
            "category",
            "purchase_date",
            "amount_egp",
            "usd_rate",
            "amount_usd",
            "quantity",
            "notes",
        ]

        for field in fields:
            if field in data:
                setattr(item, field, data[field])

        item.save()

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(AssetFurniture, pk=pk)
        item.delete()

        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class AssetFurnitureCategoriesView(View):
    def get(self, request):
        from core.constants import FURNITURE_CATEGORIES
        return JsonResponse({"categories": FURNITURE_CATEGORIES})


