# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: single-resource file. If it grows past ~200 lines, split it and
move the resulting files into a settings/<domain>/ subfolder (see
settings/ai/ or settings/gold/ for the pattern: an empty __init__.py plus
one file per concern), then update core/views/settings/__init__.py."""

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from core.models import (
    ReminderRule,
    ReminderLog,
    REMINDER_TYPE_CHOICES,
    SALARY_TRIGGER_CHOICES,
)

from core.services.shared.reminder_automation_service import ReminderAutomationService
from core.validators import _api_auth_required, _owned_queryset, _owned_object_or_404


@method_decorator(csrf_exempt, name="dispatch")
class ReminderRuleListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        rules = _owned_queryset(ReminderRule, request)
        return JsonResponse(
            {
                "rules": [r.to_dict() for r in rules],
                "rule_types": [
                    {"value": v, "label": l} for v, l in REMINDER_TYPE_CHOICES
                ],
                "salary_triggers": [
                    {"value": v, "label": l} for v, l in SALARY_TRIGGER_CHOICES
                ],
            }
        )

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        data = json.loads(request.body)
        rule = ReminderRule.objects.create(
            owner=request.user,
            name=data["name"],
            rule_type=data.get("rule_type", "cert_maturity"),
            is_active=data.get("is_active", True),
            days_before=int(data.get("days_before", 30)),
            salary_trigger=data.get("salary_trigger", "day_of_month"),
            salary_day=int(data.get("salary_day", 25)),
            salary_message=data.get("salary_message", ""),
        )
        return JsonResponse({"rule": rule.to_dict()}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class ReminderRuleDetailView(View):
    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        rule = _owned_object_or_404(ReminderRule, pk, request)
        data = json.loads(request.body)
        rule.name = data.get("name", rule.name)
        rule.rule_type = data.get("rule_type", rule.rule_type)
        rule.is_active = data.get("is_active", rule.is_active)
        rule.days_before = int(data.get("days_before", rule.days_before))
        rule.salary_trigger = data.get("salary_trigger", rule.salary_trigger)
        rule.salary_day = int(data.get("salary_day", rule.salary_day))
        rule.salary_message = data.get("salary_message", rule.salary_message)
        rule.save()
        return JsonResponse({"rule": rule.to_dict()})

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        rule = _owned_object_or_404(ReminderRule, pk, request)
        rule.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class ReminderCheckView(View):
    """Called on page load — evaluates all active rules and returns due reminders."""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        result = ReminderAutomationService().evaluate(request.user, today=timezone.localdate()).to_dict()
        return JsonResponse(result)


@method_decorator(csrf_exempt, name="dispatch")
class ReminderLogListView(View):
    """Return recent reminder log entries."""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        limit = int(request.GET.get("limit", 30))
        logs = ReminderLog.objects.select_related("rule").filter(rule__owner=request.user)[:limit]
        return JsonResponse({"logs": [l.to_dict() for l in logs]})

    def delete(self, request):
        """Clear all log entries (reset fired state) for the current user."""
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        ReminderLog.objects.filter(rule__owner=request.user).delete()
        return JsonResponse({"cleared": True})
