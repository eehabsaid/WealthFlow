import datetime
import time
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.services.balance.net_worth_service import NetWorthService
from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.wealth_growth_forecast_service import WealthGrowthForecastService
from core.services.financial_advisor.overview_service import OverviewService
from core.services.financial_advisor.risk_analysis_service import RiskAnalysisService
from core.services.financial_advisor.spending_intelligence_service import SpendingIntelligenceService
from .certificate_views import _run_certificate_interest_sync

def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None

@method_decorator(csrf_exempt, name="dispatch")
class CertificateForecastView(View):
    def get(self, request):
        _run_certificate_interest_sync()
        return JsonResponse(NetWorthService().certificate_forecast_payload(today=datetime.date.today()))

@method_decorator(csrf_exempt, name="dispatch")
class CashFlowForecastView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        payload = CashFlowForecastService(today=datetime.date.today()).payload()
        return JsonResponse(payload)

@method_decorator(csrf_exempt, name="dispatch")
class WealthGrowthForecastView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        payload = WealthGrowthForecastService(today=datetime.date.today()).payload()
        return JsonResponse(payload)

@method_decorator(csrf_exempt, name="dispatch")
class PortfolioOptimizerView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        payload = PortfolioOptimizerService(today=datetime.date.today()).payload()
        return JsonResponse(payload)

_overview_cache = None
_overview_cache_expiry = 0.0

@method_decorator(csrf_exempt, name="dispatch")
class OverviewView(View):
    def get(self, request):
        global _overview_cache, _overview_cache_expiry
        
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        now = time.time()
        if _overview_cache is not None and now < _overview_cache_expiry:
            return JsonResponse(_overview_cache)

        _run_certificate_interest_sync()
        payload = OverviewService(today=datetime.date.today()).payload()

        _overview_cache = payload
        _overview_cache_expiry = now + 30.0

        return JsonResponse(payload)

@method_decorator(csrf_exempt, name="dispatch")
class RiskAnalysisView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        payload = RiskAnalysisService(today=datetime.date.today()).payload()
        return JsonResponse(payload)

class SpendingIntelligenceView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        # We might not need _run_certificate_interest_sync since we're looking at expenses, but we use NetWorthService so let's keep the pattern.
        _run_certificate_interest_sync()
        payload = SpendingIntelligenceService(today=datetime.date.today()).payload()
        return JsonResponse(payload)
