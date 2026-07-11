# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count
from django.shortcuts import get_object_or_404
from core.models import (
    Company,
    SalaryEntry,
    PerDiem,

)
from django.db.models import Q

User = get_user_model()
from core.utils import (
    month_sort_key,
)

@method_decorator(csrf_exempt, name="dispatch")
class SalaryListView(View):
    def get(self, request):
        qs = SalaryEntry.objects.select_related("company").all()
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
        data = json.loads(request.body)
        entry = SalaryEntry.objects.create(
            company_id=data["company_id"],
            year=data["year"],
            month=data["month"],
            expected=data.get("expected", 0),
            paid=data.get("paid", 0),
            bonus=data.get("bonus", 0),
            notes=data.get("notes", ""),
        )
        return JsonResponse(entry.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class SalaryDetailView(View):
    def put(self, request, pk):
        from core.services.salary.salary_service import SalaryService
        data = json.loads(request.body)
        try:
            entry = SalaryService().update_salary(pk, data)
            return JsonResponse(entry.to_dict())
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def delete(self, request, pk):
        from core.services.salary.salary_service import SalaryService
        try:
            SalaryService().delete_salary(pk)
            return JsonResponse({"deleted": pk})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class GenerateCurrentSalaryView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}
            
        company_id = data.get("company_id")
        
        from core.services.salary.salary_service import SalaryService
        try:
            res = SalaryService().generate_current_month_salaries(company_id)
            return JsonResponse(res)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class MarkSalaryPaidView(View):
    def post(self, request, pk):
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}
        mark_paid = data.get("mark_paid", False)
        
        from core.services.salary.salary_service import SalaryService
        try:
            res = SalaryService().mark_salary_paid(pk, mark_paid)
            return JsonResponse(res)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class SalarySummaryView(View):
    def get(self, request):
        companies = Company.objects.all().order_by("order")
        result = []
        grand = {
            "total_months": 0,
            "total_expected": 0.0,
            "total_paid": 0.0,
            "total_remaining": 0.0,
            "total_bonus": 0.0,
        }
        for c in companies:
            entries = c.salary_entries.all()
            agg = entries.aggregate(
                months=Count("id", filter=Q(paid__gt=0)),
                exp=Sum("expected"),
                paid=Sum("paid"),
                bonus=Sum("bonus"),
            )
            exp = float(agg["exp"] or 0)
            paid = float(agg["paid"] or 0)
            bonus = float(agg["bonus"] or 0)
            # Calculate company total
            company_total_paid = paid + bonus
            company_total_exp = exp + bonus
            company_remaining = max(0.0, exp - paid)  # Remaining = Expected - Base Paid
            result.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "display_name": c.display_name,
                    "group_name": c.group_name,
                    "color_hex": c.color_hex,
                    "total_months": agg["months"],
                    "total_expected": company_total_exp,  # Corrected to include bonus in total expected
                    "total_paid": company_total_paid,  # Corrected to include bonus in total paid
                    "total_remaining": company_remaining,  # Remaining is still based on expected vs base paid
                    "total_bonus": bonus,
                    "years": list(
                        entries.values_list("year", flat=True)
                        .distinct()
                        .order_by("year")
                    ),
                }
            )
            grand["total_months"] += agg["months"]
            grand["total_expected"] += exp
            grand["total_paid"] += company_total_paid  # ADDED BONUS HERE
            # This ensures the grand total is the sum of the individual rows
            grand["total_remaining"] += company_remaining
            grand["total_bonus"] += bonus
        return JsonResponse({"companies": result, "grand_total": grand})

@method_decorator(csrf_exempt, name="dispatch")
class PerDiemListView(View):
    def get(self, request):
        company_id = request.GET.get("company_id") or request.GET.get("company")
        year = request.GET.get("year")
        
        if not company_id or not year:
            return JsonResponse({"error": "Missing company_id or year"}, status=400)
            
        qs = PerDiem.objects.filter(company_id=company_id, year=year).select_related("company", "currency", "bank")
        return JsonResponse({"entries": [e.to_dict() for e in qs]})

    def post(self, request):
        from core.services.salary.per_diem_service import PerDiemService
        data = json.loads(request.body)
        try:
            pd = PerDiemService().create_per_diem(data)
            return JsonResponse(pd.to_dict(), status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class PerDiemDetailView(View):
    def get(self, request, pk):
        pd = get_object_or_404(PerDiem.objects.select_related("company", "currency", "bank"), pk=pk)
        return JsonResponse(pd.to_dict())

    def put(self, request, pk):
        from core.services.salary.per_diem_service import PerDiemService
        data = json.loads(request.body)
        try:
            pd = PerDiemService().update_per_diem(pk, data)
            return JsonResponse(pd.to_dict())
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def delete(self, request, pk):
        from core.services.salary.per_diem_service import PerDiemService
        try:
            PerDiemService().delete_per_diem(pk)
            return JsonResponse({"deleted": pk})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class PerDiemCurrencyListView(View):
    def get(self, request):
        from core.services.salary.per_diem_service import PerDiemService
        try:
            currencies = PerDiemService().get_currencies_used_in_balance()
            return JsonResponse({"currencies": [c.to_dict() for c in currencies]})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

