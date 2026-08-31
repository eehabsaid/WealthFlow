import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.models.scenario import Scenario, ScenarioEvent
from core.services.financial_advisor.scenario_planner_service import create_scenario_record
from core.views.balance.forecasts.shared import _api_auth_required


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

        try:
            sc = create_scenario_record(
                name=body.get("name"),
                description=body.get("description", ""),
                is_baseline_pinned=body.get("is_baseline_pinned", False),
                events=body.get("events"),
            )
            return JsonResponse(sc.to_dict(), status=201)
        except ValueError as err:
            return JsonResponse({"error": str(err)}, status=400)


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
class ScenarioDuplicateView(View):
    def post(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        sc = Scenario.objects.filter(id=pk).prefetch_related("events").first()
        if not sc:
            return JsonResponse({"error": "Scenario not found"}, status=404)
        new_sc = Scenario.objects.create(
            name=f"{sc.name} (Copy)",
            description=sc.description or "",
            is_baseline_pinned=False,
        )
        for ev in sc.events.all():
            ScenarioEvent.objects.create(
                scenario=new_sc,
                event_type=ev.event_type,
                event_date=ev.event_date,
                params=dict(ev.params or {}),
                order=ev.order,
            )
        return JsonResponse(new_sc.to_dict(), status=201)
