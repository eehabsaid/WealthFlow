# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    Company,

)

User = get_user_model()

@method_decorator(csrf_exempt, name="dispatch")
class CompanyListView(View):
    def get(self, request):
        companies = Company.objects.all().order_by("order")
        return JsonResponse({"companies": [c.to_dict() for c in companies]})

    def post(self, request):
        data = json.loads(request.body) if request.body else {}
        name = data.get("name")
        if not name:
            return JsonResponse({"error": "name is required"}, status=400)

        company = Company.objects.create(
            name=name,
            display_name=data.get("display_name", name),
            group_name=data.get("group_name", ""),
            color_hex=data.get("color_hex", "#0d6efd"),
            is_active=data.get("is_active", True),
            order=data.get("order", 0),
            current_salary_amount=data.get("current_salary_amount", 0),
            current_salary_currency_id=data.get("current_salary_currency_id"),
            payment_day=data.get("payment_day", 25),
            default_bank_id=data.get("default_bank_id"),
            per_diem_amount=data.get("per_diem_amount", 0),
            per_diem_currency_id=data.get("per_diem_currency_id"),
            bonus_amount=data.get("bonus_amount", 0),
            payroll_notes=data.get("payroll_notes", ""),
        )
        return JsonResponse(company.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class CompanyDetailView(View):
    def get(self, request, pk):
        c = get_object_or_404(
            Company.objects.select_related(
                "current_salary_currency", "default_bank", "per_diem_currency"
            ),
            pk=pk,
        )
        return JsonResponse(c.to_dict())

    def put(self, request, pk):
        c = get_object_or_404(Company, pk=pk)
        data = json.loads(request.body)
        for field in [
            "name",
            "display_name",
            "group_name",
            "color_hex",
            "is_active",
            "order",
            "current_salary_amount",
            "current_salary_currency_id",
            "payment_day",
            "default_bank_id",
            "per_diem_amount",
            "per_diem_currency_id",
            "bonus_amount",
            "payroll_notes",
        ]:
            if field in data:
                setattr(c, field, data[field])
        c.save()
        return JsonResponse(c.to_dict())

    def delete(self, request, pk):
        c = get_object_or_404(Company, pk=pk)
        c.delete()
        return JsonResponse({"deleted": pk})

