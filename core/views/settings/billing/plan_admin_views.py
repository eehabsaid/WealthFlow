# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: part of the settings/billing/ domain package. If this file
grows past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404

from core.models import Plan
from core.views.auth_views import AdminRequiredMixin

EDITABLE_FIELDS = ["name", "price_egp", "price_usd", "billing_interval_days", "is_active", "sort_order"]


@method_decorator(csrf_exempt, name="dispatch")
class PlanAdminListView(AdminRequiredMixin, View):
    """Lists every plan, including inactive ones — unlike the public
    /api/billing/plans/ endpoint, which only returns active plans."""

    def get(self, request):
        plans = Plan.objects.all().order_by("sort_order", "id")
        return JsonResponse({"plans": [p.to_dict() for p in plans]})


@method_decorator(csrf_exempt, name="dispatch")
class PlanAdminDetailView(AdminRequiredMixin, View):
    def get(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        return JsonResponse(plan.to_dict())

    def put(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        data = json.loads(request.body)
        for field in EDITABLE_FIELDS:
            if field in data:
                setattr(plan, field, data[field])
        plan.save()
        return JsonResponse(plan.to_dict())
