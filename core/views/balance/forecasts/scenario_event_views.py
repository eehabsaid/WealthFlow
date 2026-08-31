import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.models.scenario import Scenario, ScenarioEvent
from core.services.financial_advisor.scenario_planner_service import (
    EVENT_SCHEMA,
    SCENARIO_EVENT_SCHEMA_VERSION,
)
from core.views.balance.forecasts.shared import _api_auth_required


@method_decorator(csrf_exempt, name="dispatch")
class ScenarioEventDefinitionsView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        return JsonResponse({"schema_version": SCENARIO_EVENT_SCHEMA_VERSION, "event_schema": EVENT_SCHEMA})


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
