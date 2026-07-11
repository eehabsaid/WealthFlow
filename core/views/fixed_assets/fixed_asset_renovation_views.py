# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    AssetRenovation,

)


@method_decorator(csrf_exempt, name="dispatch")
class AssetRenovationListView(View):

    def get(self, request):
        asset_id = request.GET.get("asset")

        qs = AssetRenovation.objects.all().order_by("date", "id")

        if asset_id:
            qs = qs.filter(asset_id=asset_id)

        return JsonResponse({
            "renovations": [r.to_dict() for r in qs]
        })

    def post(self, request):
        data = json.loads(request.body)

        item = AssetRenovation.objects.create(
            asset_id=data["asset_id"],
            date=data["date"],
            category=data["category"],
            description=data.get("description", ""),
            amount_egp=data.get("amount_egp", 0),
            usd_rate=data.get("usd_rate", 0),
            amount_usd=data.get("amount_usd", 0),
            notes=data.get("notes", ""),
        )

        return JsonResponse(item.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class AssetRenovationDetailView(View):

    def put(self, request, pk):
        item = get_object_or_404(AssetRenovation, pk=pk)

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
                setattr(item, field, data[field])

        item.save()

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(AssetRenovation, pk=pk)
        item.delete()

        return JsonResponse({"deleted": pk})


