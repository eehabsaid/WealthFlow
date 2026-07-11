# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.shortcuts import get_object_or_404
from core.models import (
    ReminderRule,
    CertificateStatus,
    ReminderLog,
    REMINDER_TYPE_CHOICES,
    SALARY_TRIGGER_CHOICES,
    FixedAsset,

)

from core.services.fixed_assets.property_valuation_service import PropertyValuationService
from core.services.shared.reminder_automation_service import ReminderAutomationService

User = get_user_model()

@method_decorator(csrf_exempt, name="dispatch")
class ReminderRuleListView(View):
    def get(self, request):
        rules = ReminderRule.objects.all()
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
        data = json.loads(request.body)
        rule = ReminderRule.objects.create(
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
        rule = get_object_or_404(ReminderRule, pk=pk)
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
        rule = get_object_or_404(ReminderRule, pk=pk)
        rule.delete()
        return JsonResponse({"deleted": pk})

@method_decorator(csrf_exempt, name="dispatch")
class ReminderCheckView(View):
    """Called on page load — evaluates all active rules and returns due reminders."""

    def get(self, request):
        result = ReminderAutomationService().evaluate(today=timezone.localdate()).to_dict()
        return JsonResponse(result)

@method_decorator(csrf_exempt, name="dispatch")
class FixedAssetValuationRefreshView(View):
    def post(self, request, pk):
        asset = get_object_or_404(FixedAsset, pk=pk)
        updated, provider_name = PropertyValuationService().refresh_asset(asset, today=timezone.localdate())
        asset.refresh_from_db()
        return JsonResponse(
            {
                "updated": updated,
                "provider": provider_name,
                "asset": asset.to_dict(),
            }
        )

def _salary_trigger_day(rule, today):
    """Compute the calendar day this rule fires on for the given month."""
    import calendar as cal

    last_day = cal.monthrange(today.year, today.month)[1]
    if rule.salary_trigger == "day_of_month":
        return min(rule.salary_day, last_day)
    elif rule.salary_trigger == "days_before_eom":
        return max(1, last_day - rule.salary_day)
    elif rule.salary_trigger == "days_after_som":
        return min(rule.salary_day + 1, last_day)
    return rule.salary_day

@method_decorator(csrf_exempt, name="dispatch")
class ReminderLogListView(View):
    """Return recent reminder log entries."""

    def get(self, request):
        limit = int(request.GET.get("limit", 30))
        logs = ReminderLog.objects.select_related("rule").all()[:limit]
        return JsonResponse({"logs": [l.to_dict() for l in logs]})

    def delete(self, request):
        """Clear all log entries (reset fired state)."""
        ReminderLog.objects.all().delete()
        return JsonResponse({"cleared": True})

# ════════════════════════════════════════════════════════════════════════════
# CERTIFICATE STATUS VIEWS
# ════════════════════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name="dispatch")
class CertificateStatusListView(View):
    def get(self, request):
        statuses = CertificateStatus.objects.all()
        return JsonResponse({"statuses": [s.to_dict() for s in statuses]})

    def post(self, request):
        data = json.loads(request.body)
        # If new status is default, unset any existing default
        if data.get("is_default"):
            CertificateStatus.objects.filter(is_default=True).update(is_default=False)
        s = CertificateStatus.objects.create(
            name=data["name"],
            color_hex=data.get("color_hex", "#1a6ef5"),
            is_default=data.get("is_default", False),
            is_terminal=data.get("is_terminal", False),
            order=int(data.get("order", 0)),
        )
        return JsonResponse({"status": s.to_dict()}, status=201)

@method_decorator(csrf_exempt, name="dispatch")
class CertificateStatusDetailView(View):
    def put(self, request, pk):
        s = get_object_or_404(CertificateStatus, pk=pk)
        data = json.loads(request.body)
        if data.get("is_default") and not s.is_default:
            CertificateStatus.objects.filter(is_default=True).update(is_default=False)
        s.name = data.get("name", s.name)
        s.color_hex = data.get("color_hex", s.color_hex)
        s.is_default = data.get("is_default", s.is_default)
        s.is_terminal = data.get("is_terminal", s.is_terminal)
        s.order = int(data.get("order", s.order))
        s.save()
        return JsonResponse({"status": s.to_dict()})

    def delete(self, request, pk):
        s = get_object_or_404(CertificateStatus, pk=pk)
        s.delete()
        return JsonResponse({"deleted": pk})

# ════════════════════════════════════════════════════════════════════════════
# ADVANCED REPORTS VIEWS
# ════════════════════════════════════════════════════════════════════════════

