import datetime
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.services.financial_advisor.scenario_planner_service import ScenarioPlannerService
from core.views.certificate_views import _run_certificate_interest_sync
from core.views.balance.forecasts.shared import _api_auth_required


@method_decorator(csrf_exempt, name="dispatch")
class ScenarioComparisonView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()

        raw_ids = request.GET.get("scenario_ids", "")
        scenario_ids = []
        if raw_ids:
            for item in raw_ids.split(","):
                item_str = item.strip()
                if item_str.isdigit():
                    scenario_ids.append(int(item_str))

        svc = ScenarioPlannerService(today=datetime.date.today(), user=request.user)
        payload = svc.payload(scenario_ids=scenario_ids)
        return JsonResponse(payload)
