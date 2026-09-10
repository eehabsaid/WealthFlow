import datetime
import time
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.services.balance.net_worth_service import NetWorthService
from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.financial_advisor.cash_flow_forecast_service.custom_projection import compute_custom_cash_projection
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.wealth_growth_forecast_service import WealthGrowthForecastService
from core.services.financial_advisor.overview_service import OverviewService
from core.views.certificate_views import _run_certificate_interest_sync
from core.views.balance.forecasts.shared import _api_auth_required


@method_decorator(csrf_exempt, name="dispatch")
class CertificateForecastView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        return JsonResponse(NetWorthService(request.user).certificate_forecast_payload(today=datetime.date.today()))


@method_decorator(csrf_exempt, name="dispatch")
class CashFlowForecastView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        payload = CashFlowForecastService(request.user, today=datetime.date.today()).payload()
        return JsonResponse(payload)


@method_decorator(csrf_exempt, name="dispatch")
class CashFlowCustomProjectionView(View):
    """
    Interactive "what-if" cash projection: pick a target date, exclude
    specific recurring event types (salary, rental, mortgage, certificate
    events), choose EGP-only vs total-liquid currency scope. Backs the
    custom projection card in the Cash Flow tab. Pure deterministic
    computation — see custom_projection.py — never an LLM estimate.
    """

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()

        today = datetime.date.today()

        target_date_str = request.GET.get("target_date")
        if target_date_str:
            try:
                target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"error": "invalid target_date, expected YYYY-MM-DD"}, status=400)
        else:
            days_param = request.GET.get("days")
            if days_param is not None:
                try:
                    days = int(days_param)
                except ValueError:
                    return JsonResponse(
                        {"error": f"invalid days value: {days_param!r}, expected an integer"}, status=400
                    )
            else:
                days = 30
            target_date = today + datetime.timedelta(days=max(1, days))

        if target_date <= today:
            return JsonResponse({"error": "target_date must be in the future"}, status=400)

        exclude_param = request.GET.get("exclude", "")
        exclude_types = [t.strip() for t in exclude_param.split(",") if t.strip()]

        currency_scope = request.GET.get("currency_scope", "egp_only")

        payload = compute_custom_cash_projection(
            request.user,
            today=today,
            target_date=target_date,
            exclude_event_types=exclude_types,
            currency_scope=currency_scope,
        )
        return JsonResponse(payload)


@method_decorator(csrf_exempt, name="dispatch")
class WealthGrowthForecastView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        payload = WealthGrowthForecastService(request.user, today=datetime.date.today()).payload()
        return JsonResponse(payload)


@method_decorator(csrf_exempt, name="dispatch")
class PortfolioOptimizerView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        payload = PortfolioOptimizerService(request.user, today=datetime.date.today()).payload()
        return JsonResponse(payload)


# Keyed by user id so one user's cached payload is never served to another
# — a bare module-level (payload, expiry) tuple would leak across users.
_overview_cache: dict = {}


@method_decorator(csrf_exempt, name="dispatch")
class OverviewView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        now = time.time()
        cached = _overview_cache.get(request.user.id)
        if cached is not None:
            payload, expiry = cached
            if now < expiry:
                return JsonResponse(payload)

        _run_certificate_interest_sync()
        payload = OverviewService(request.user, today=datetime.date.today()).payload()

        _overview_cache[request.user.id] = (payload, now + 30.0)

        return JsonResponse(payload)
