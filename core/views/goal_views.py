from core.views.certificate_views import _run_certificate_interest_sync
# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    Goal,

)

import datetime
from core.services.financial_advisor.goal_planning_service import GoalPlanningService

User = get_user_model()
from core.utils import (
    _parse_iso_date,
)
from core.validators import _api_auth_required

@method_decorator(csrf_exempt, name="dispatch")
class GoalPlanningView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        _run_certificate_interest_sync()
        payload = GoalPlanningService(today=datetime.date.today()).payload()
        return JsonResponse(payload)

@method_decorator(csrf_exempt, name="dispatch")
class GoalListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        goals = Goal.objects.select_related("currency", "linked_asset").all().order_by("target_date", "id")
        return JsonResponse({"goals": [goal.to_dict() for goal in goals]})

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        data = json.loads(request.body or "{}")
        goal = Goal.objects.create(
            name=data.get("name", "").strip(),
            goal_type=data.get("goal_type", "").strip(),
            target_amount=data.get("target_amount", 0) or 0,
            currency_id=data.get("currency_id") or None,
            target_date=_parse_iso_date(data.get("target_date")),
            current_saved_amount=data.get("current_saved_amount", 0) or 0,
            linked_asset_id=data.get("linked_asset_id") or None,
            priority=data.get("priority", "Medium"),
            notes=data.get("notes", ""),
        )
        return JsonResponse(goal.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class GoalDetailView(View):
    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        goal = get_object_or_404(Goal, pk=pk)
        data = json.loads(request.body or "{}")

        for field in ["name", "goal_type", "target_amount", "current_saved_amount", "priority", "notes"]:
            if field in data:
                setattr(goal, field, data[field])

        if "currency_id" in data:
            goal.currency_id = data.get("currency_id") or None
        if "linked_asset_id" in data:
            goal.linked_asset_id = data.get("linked_asset_id") or None
        if "target_date" in data:
            goal.target_date = _parse_iso_date(data.get("target_date"))

        goal.save()
        return JsonResponse(goal.to_dict())

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        goal = get_object_or_404(Goal, pk=pk)
        goal.delete()
        return JsonResponse({"deleted": pk})

# ============================================================
# Fixed Assets APIs
# ============================================================

