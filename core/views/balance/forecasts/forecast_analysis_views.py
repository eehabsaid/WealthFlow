import datetime
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.services.financial_advisor.risk_analysis_service import RiskAnalysisService
from core.services.financial_advisor.spending_intelligence_service import SpendingIntelligenceService
from core.services.financial_advisor.opportunity_detection_service import OpportunityDetectionService
from core.services.financial_advisor.performance_service import PerformanceService
from core.services.financial_advisor.what_if_simulator_service import WhatIfSimulatorService
from core.views.certificate_views import _run_certificate_interest_sync
from core.views.balance.forecasts.shared import _api_auth_required


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
