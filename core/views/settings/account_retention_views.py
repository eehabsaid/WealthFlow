"""Account-deletion grace period setting (sysadmin-only; shown on the Legal Text tab, where the
retention wording lives). Stored as the global AppSettings key `account_deletion_grace_days`."""

from django.http import JsonResponse
from django.views import View

from core.authentication.services import AuthWorkflowService
from core.authentication.views.mixins import SysadminRequiredMixin
from core.constants.account_retention import DEFAULT_GRACE_DAYS, GRACE_DAYS_KEY, grace_days
from core.models import AppSettings
from core.validators.json_body import parse_json_body

MIN_GRACE_DAYS = 1
MAX_GRACE_DAYS = 365


def _payload():
    return {"grace_days": grace_days(), "default": DEFAULT_GRACE_DAYS, "min": MIN_GRACE_DAYS, "max": MAX_GRACE_DAYS}


class AccountRetentionView(SysadminRequiredMixin, View):
    def get(self, request):
        return JsonResponse(_payload())

    def post(self, request):
        raw = parse_json_body(request).get("grace_days")
        if isinstance(raw, bool):
            return JsonResponse({"error": "invalid_grace_days"}, status=400)
        try:
            days = int(str(raw).strip())
        except (TypeError, ValueError):
            return JsonResponse({"error": "invalid_grace_days"}, status=400)
        if not MIN_GRACE_DAYS <= days <= MAX_GRACE_DAYS:
            return JsonResponse({"error": "invalid_grace_days"}, status=400)
        previous = grace_days()
        AppSettings.set(GRACE_DAYS_KEY, str(days))
        if previous != days:
            AuthWorkflowService.record_audit(
                request.user, "account_grace_days_changed", actor=request.user, details=f"from={previous} to={days}"
            )
        return JsonResponse(_payload())
