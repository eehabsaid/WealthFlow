# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: part of the settings/billing/ domain package. If this file
grows past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

import json
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.utils.text import slugify
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404

from core.models import Plan
from core.views.auth_views import AdminRequiredMixin

EDITABLE_FIELDS = ["name", "billing_interval_days", "is_active", "sort_order"]


def _unique_code_from_name(name: str) -> str:
    base = slugify(name)[:30] or "plan"
    code = base
    n = 2
    while Plan.objects.filter(code=code).exists():
        suffix = f"-{n}"
        code = f"{base[: 30 - len(suffix)]}{suffix}"
        n += 1
    return code


@method_decorator(csrf_exempt, name="dispatch")
class PlanAdminListView(AdminRequiredMixin, View):
    """Lists every plan, including inactive ones — unlike the public
    /api/billing/plans/ endpoint, which only returns active plans."""

    def get(self, request):
        plans = Plan.objects.all().order_by("sort_order", "id")
        return JsonResponse({"plans": [p.to_dict() for p in plans]})

    def post(self, request):
        data = json.loads(request.body)
        name = (data.get("name") or "").strip()
        if not name:
            return JsonResponse({"error": "Plan name is required."}, status=400)
        plan = Plan.objects.create(
            code=_unique_code_from_name(name),
            name=name,
            billing_interval_days=data.get("billing_interval_days", 30),
            is_active=data.get("is_active", True),
            sort_order=data.get("sort_order", 0),
        )
        return JsonResponse(plan.to_dict(), status=201)


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

    def delete(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        try:
            plan.delete()
        except ProtectedError:
            return JsonResponse(
                {"error": "This plan has subscribers and can't be deleted. Deactivate it instead."},
                status=409,
            )
        return JsonResponse({"deleted": pk})
