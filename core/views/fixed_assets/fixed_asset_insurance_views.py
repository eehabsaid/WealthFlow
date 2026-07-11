# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    AssetInsurance,

)

@method_decorator(csrf_exempt, name="dispatch")
class AssetInsuranceListView(View):

    def get(self, request):
        asset_id = request.GET.get("asset")

        qs = AssetInsurance.objects.all().order_by("expiry_date", "id")

        if asset_id:
            qs = qs.filter(asset_id=asset_id)

        return JsonResponse({
            "insurance": [i.to_dict() for i in qs]
        })

    def post(self, request):
        data = json.loads(request.body)

        item = AssetInsurance.objects.create(
            asset_id=data["asset_id"],
            company=data["company"],
            policy_number=data.get("policy_number", ""),
            expiry_date=data.get("expiry_date") or None,
            premium=data.get("premium", 0),
        )

        return JsonResponse(item.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class AssetInsuranceDetailView(View):

    def put(self, request, pk):
        item = get_object_or_404(AssetInsurance, pk=pk)

        data = json.loads(request.body)

        fields = ["company", "policy_number", "expiry_date", "premium"]

        for field in fields:
            if field in data:
                setattr(item, field, data[field])

        item.save()

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(AssetInsurance, pk=pk)
        item.delete()

        return JsonResponse({"deleted": pk})

