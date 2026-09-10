# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from core.models import PerDiem
from core.validators import _api_auth_required, _child_owned_object_or_404

@method_decorator(csrf_exempt, name="dispatch")
class PerDiemListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        company_id = request.GET.get("company_id") or request.GET.get("company")
        year = request.GET.get("year")

        if not company_id or not year:
            return JsonResponse({"error": "Missing company_id or year"}, status=400)

        qs = PerDiem.objects.filter(
            company_id=company_id, company__owner=request.user, year=year
        ).select_related("company", "currency", "bank")
        return JsonResponse({"entries": [e.to_dict() for e in qs]})

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.services.salary.per_diem_service import PerDiemService
        data = json.loads(request.body)
        try:
            pd = PerDiemService().create_per_diem(data, request.user)
            return JsonResponse(pd.to_dict(), status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class PerDiemDetailView(View):
    def get(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        pd = _child_owned_object_or_404(
            PerDiem.objects.select_related("company", "currency", "bank"),
            pk, request, parent_field="company",
        )
        return JsonResponse(pd.to_dict())

    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.services.salary.per_diem_service import PerDiemService
        data = json.loads(request.body)
        try:
            pd = PerDiemService().update_per_diem(pk, data, request.user)
            return JsonResponse(pd.to_dict())
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.services.salary.per_diem_service import PerDiemService
        try:
            PerDiemService().delete_per_diem(pk, request.user)
            return JsonResponse({"deleted": pk})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class PerDiemCurrencyListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.services.salary.per_diem_service import PerDiemService
        try:
            currencies = PerDiemService().get_currencies_used_in_balance(request.user)
            return JsonResponse({"currencies": [c.to_dict() for c in currencies]})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
