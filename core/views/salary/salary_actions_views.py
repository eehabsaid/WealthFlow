# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count, Q
from core.models import Company
from core.validators import _api_auth_required

@method_decorator(csrf_exempt, name="dispatch")
class GenerateCurrentSalaryView(View):
    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}

        company_id = data.get("company_id")

        from core.services.salary.salary_service import SalaryService
        try:
            res = SalaryService().generate_current_month_salaries(request.user, company_id)
            return JsonResponse(res)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class MarkSalaryPaidView(View):
    def post(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}
        mark_paid = data.get("mark_paid", False)

        from core.services.salary.salary_service import SalaryService
        try:
            res = SalaryService().mark_salary_paid(pk, mark_paid, request.user)
            return JsonResponse(res)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class SalarySummaryView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        companies = Company.objects.filter(owner=request.user).order_by("order")
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
            company_total_paid = paid + bonus
            company_total_exp = exp + bonus
            company_remaining = max(0.0, exp - paid)
            result.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "display_name": c.display_name,
                    "group_name": c.group_name,
                    "color_hex": c.color_hex,
                    "total_months": agg["months"],
                    "total_expected": company_total_exp,
                    "total_paid": company_total_paid,
                    "total_remaining": company_remaining,
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
            grand["total_paid"] += company_total_paid
            grand["total_remaining"] += company_remaining
            grand["total_bonus"] += bonus
        return JsonResponse({"companies": result, "grand_total": grand})
