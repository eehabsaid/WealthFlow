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


import json
from core.models.scenario import Scenario, ScenarioEvent
from core.services.financial_advisor.scenario_planner_service import (
    ScenarioPlannerService,
    EVENT_SCHEMA,
)


@method_decorator(csrf_exempt, name="dispatch")
class ScenarioEventDefinitionsView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        return JsonResponse({"event_schema": EVENT_SCHEMA})


@method_decorator(csrf_exempt, name="dispatch")
class ScenarioListCreateView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        scenarios = [sc.to_dict() for sc in Scenario.objects.all()]
        return JsonResponse({"scenarios": scenarios})

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        name = str(body.get("name", "")).strip()
        if not name:
            return JsonResponse({"error": "Name is required"}, status=400)

        sc = Scenario.objects.create(
            name=name,
            description=str(body.get("description", "")).strip(),
            is_baseline_pinned=bool(body.get("is_baseline_pinned", False)),
        )
        return JsonResponse(sc.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class ScenarioDetailView(View):
    def get(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            sc = Scenario.objects.get(pk=pk)
            return JsonResponse(sc.to_dict())
        except Scenario.DoesNotExist:
            return JsonResponse({"error": "Scenario not found"}, status=404)

    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            sc = Scenario.objects.get(pk=pk)
        except Scenario.DoesNotExist:
            return JsonResponse({"error": "Scenario not found"}, status=404)

        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        if "name" in body:
            name = str(body["name"]).strip()
            if name:
                sc.name = name
        if "description" in body:
            sc.description = str(body["description"]).strip()
        if "is_baseline_pinned" in body:
            sc.is_baseline_pinned = bool(body["is_baseline_pinned"])

        sc.save()
        return JsonResponse(sc.to_dict())

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            sc = Scenario.objects.get(pk=pk)
            sc.delete()
            return JsonResponse({"status": "deleted"})
        except Scenario.DoesNotExist:
            return JsonResponse({"error": "Scenario not found"}, status=404)


@method_decorator(csrf_exempt, name="dispatch")
class ScenarioEventListCreateView(View):
    def get(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            sc = Scenario.objects.get(pk=pk)
            events = [ev.to_dict() for ev in sc.events.all()]
            return JsonResponse({"events": events})
        except Scenario.DoesNotExist:
            return JsonResponse({"error": "Scenario not found"}, status=404)

    def post(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            sc = Scenario.objects.get(pk=pk)
        except Scenario.DoesNotExist:
            return JsonResponse({"error": "Scenario not found"}, status=404)

        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        event_type = str(body.get("event_type", "")).strip()
        event_date = body.get("event_date")
        if not event_type or not event_date:
            return JsonResponse({"error": "event_type and event_date are required"}, status=400)

        ev = ScenarioEvent.objects.create(
            scenario=sc,
            event_type=event_type,
            event_date=event_date,
            params=body.get("params", {}),
            order=int(body.get("order", 0)),
        )
        return JsonResponse(ev.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class ScenarioEventDetailView(View):
    def _get_event(self, pk, event_id):
        return ScenarioEvent.objects.filter(scenario_id=pk, id=event_id).first()

    def get(self, request, pk, event_id):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        ev = self._get_event(pk, event_id)
        if not ev:
            return JsonResponse({"error": "Event not found"}, status=404)
        return JsonResponse(ev.to_dict())

    def put(self, request, pk, event_id):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        ev = self._get_event(pk, event_id)
        if not ev:
            return JsonResponse({"error": "Event not found"}, status=404)

        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        if "event_type" in body:
            ev.event_type = str(body["event_type"]).strip()
        if "event_date" in body:
            ev.event_date = body["event_date"]
        if "params" in body:
            ev.params = body["params"]
        if "order" in body:
            ev.order = int(body["order"])

        ev.save()
        return JsonResponse(ev.to_dict())

    def delete(self, request, pk, event_id):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        ev = self._get_event(pk, event_id)
        if not ev:
            return JsonResponse({"error": "Event not found"}, status=404)
        ev.delete()
        return JsonResponse({"status": "deleted"})


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

        svc = ScenarioPlannerService(today=datetime.date.today())
        payload = svc.payload(scenario_ids=scenario_ids)
        return JsonResponse(payload)

