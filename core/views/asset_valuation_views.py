# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""Split out of the old reminder_views.py, where it lived only because it
happened to import PropertyValuationService alongside the reminder code —
it isn't reminder- or settings-related. Called from the Fixed Assets
detail view's "refresh valuation" action, so it stays a plain top-level
view rather than moving under core/views/settings/.

_salary_trigger_day here is a module-level duplicate of
ReminderAutomationService._salary_trigger_day (core/services/shared/
reminder_automation_service.py) — kept as-is (unused, but re-exported via
core/views/__init__.py, so not removed as part of this structural move)."""

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.shortcuts import get_object_or_404
from core.models import FixedAsset

from core.services.fixed_assets.property_valuation_service import PropertyValuationService


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
