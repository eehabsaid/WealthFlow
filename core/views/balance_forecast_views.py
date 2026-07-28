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
from core.services.financial_advisor.opportunity_detection_service import OpportunityDetectionService
from core.services.financial_advisor.performance_service import PerformanceService
from core.services.financial_advisor.what_if_simulator_service import WhatIfSimulatorService
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

class OpportunityDetectionView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        payload = OpportunityDetectionService(today=datetime.date.today()).payload()
        return JsonResponse(payload)


class PerformanceView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        payload = PerformanceService(today=datetime.date.today()).payload()
        return JsonResponse(payload)


class WhatIfSimulatorView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()

        def _qparam_float(name, default=0.0):
            try:
                return float(request.GET.get(name, default))
            except (TypeError, ValueError):
                return float(default)

        salary_change_pct = _qparam_float("salary_change_pct", 0.0)
        expenses_change_pct = _qparam_float("expenses_change_pct", 0.0)
        certificate_reinvestment_choice = str(
            request.GET.get("certificate_reinvestment_choice", "reinvest")
        ).strip()

        gold_param = request.GET.get("gold_allocation_target_pct")
        gold_allocation_target_pct = None
        if gold_param is not None:
            try:
                gold_allocation_target_pct = float(gold_param)
            except (TypeError, ValueError):
                gold_allocation_target_pct = None

        payload = WhatIfSimulatorService(today=datetime.date.today()).payload(
            salary_change_pct=salary_change_pct,
            expenses_change_pct=expenses_change_pct,
            gold_allocation_target_pct=gold_allocation_target_pct,
            certificate_reinvestment_choice=certificate_reinvestment_choice,
        )
        return JsonResponse(payload)
