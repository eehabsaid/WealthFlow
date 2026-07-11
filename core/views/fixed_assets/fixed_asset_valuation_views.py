# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    AssetValuationHistory,

)

@method_decorator(csrf_exempt, name="dispatch")
class AssetValuationHistoryListView(View):

    def get(self, request):
        asset_id = request.GET.get("asset")

        qs = AssetValuationHistory.objects.all().order_by(
            "-valuation_date",
            "-id",
        )

        if asset_id:
            qs = qs.filter(asset_id=asset_id)

        return JsonResponse({
            "valuation_history": [
                v.to_dict() for v in qs
            ]
        })

    def post(self, request):
        data = json.loads(request.body)

        item = AssetValuationHistory.objects.create(
            asset_id=data["asset_id"],
            valuation_date=data["valuation_date"],
            market_value=data["market_value"],
            valuation_source=data.get(
                "valuation_source",
                "Manual",
            ),
            notes=data.get("notes", ""),
        )

        asset = item.asset
        asset.current_market_value = item.market_value
        asset.last_valuation_date = item.valuation_date
        asset.valuation_source = item.valuation_source
        asset.save()

        return JsonResponse(item.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class AssetValuationHistoryDetailView(View):

    def put(self, request, pk):
        item = get_object_or_404(
            AssetValuationHistory,
            pk=pk,
        )

        data = json.loads(request.body)

        fields = [
            "valuation_date",
            "market_value",
            "valuation_source",
            "notes",
        ]

        for field in fields:
            if field in data:
                setattr(item, field, data[field])

        item.save()

        asset = item.asset
        asset.current_market_value = item.market_value
        asset.last_valuation_date = item.valuation_date
        asset.valuation_source = item.valuation_source
        asset.save()

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(
            AssetValuationHistory,
            pk=pk,
        )
        item.delete()

        return JsonResponse({"deleted": pk})

