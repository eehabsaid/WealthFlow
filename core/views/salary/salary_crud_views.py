# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from core.models import Company, SalaryEntry
from core.validators import _api_auth_required
from core.utils import month_sort_key

@method_decorator(csrf_exempt, name="dispatch")
class SalaryListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        qs = SalaryEntry.objects.select_related("company").filter(company__owner=request.user)
        company_id = request.GET.get("company")
        year = request.GET.get("year")
        if company_id:
            qs = qs.filter(company_id=company_id)
        if year:
            qs = qs.filter(year=year)
        return JsonResponse(
            {"entries": sorted([e.to_dict() for e in qs], key=month_sort_key)}
        )

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        data = json.loads(request.body) if request.body else {}
        company_id = data.get("company_id")
        year = data.get("year")
        month = data.get("month")
        if not company_id or not year or not month:
            return JsonResponse({"error": "company_id, year, and month are required"}, status=400)

        company = Company.objects.filter(id=company_id, owner=request.user).first()
        if not company:
            return JsonResponse({"error": "company not found"}, status=404)

        entry = SalaryEntry.objects.create(
            company=company,
            year=year,
            month=month,
            expected=data.get("expected", 0),
            paid=data.get("paid", 0),
            bonus=data.get("bonus", 0),
            notes=data.get("notes", ""),
        )
        return JsonResponse(entry.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class SalaryDetailView(View):
    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.services.salary.salary_service import SalaryService
        data = json.loads(request.body)
        try:
            entry = SalaryService().update_salary(pk, data, request.user)
            return JsonResponse(entry.to_dict())
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.services.salary.salary_service import SalaryService
        try:
            SalaryService().delete_salary(pk, request.user)
            return JsonResponse({"deleted": pk})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
