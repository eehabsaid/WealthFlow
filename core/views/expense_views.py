# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from core.models import Expense

User = get_user_model()

@method_decorator(csrf_exempt, name="dispatch")
class ExpenseListView(View):
    def get(self, request):
        qs = Expense.objects.select_related("category", "subcategory", "currency", "bank").all()

        year = request.GET.get("year")
        month = request.GET.get("month")
        cat_id = request.GET.get("category")
        search = request.GET.get("search", "").strip()

        start_date = request.GET.get("start")
        end_date = request.GET.get("end")

        if start_date and end_date:
            qs = qs.filter(date__gte=start_date, date__lte=end_date)
        else:
            if year:
                qs = qs.filter(year=int(year))

            if month:
                qs = qs.filter(month=int(month))

        if cat_id:
            qs = qs.filter(category_id=int(cat_id))

        if search:
            qs = qs.filter(description__icontains=search) | qs.filter(
                notes__icontains=search
            )

        entries = [e.to_dict() for e in qs]

        total = sum(float(e.amount_egp or 0) for e in qs)

        return JsonResponse({"entries": entries, "total": total})

    def post(self, request):
        data = json.loads(request.body)
        from core.services import ExpenseService
        try:
            exp = ExpenseService.create_expense(data)
        except ValueError as exc:
            if str(exc) == "bank_account_required":
                return JsonResponse(
                    {
                        "error": "Bank account is required for this payment method",
                        "error_key": "bank_account_required",
                    },
                    status=400,
                )
            if str(exc) == "matching_balance_entry_not_found":
                return JsonResponse(
                    {
                        "error": "Matching balance entry not found",
                        "error_key": "matching_balance_not_found",
                    },
                    status=400,
                )
            if str(exc) == "insufficient_balance":
                return JsonResponse(
                    {
                        "error": "insufficient_balance",
                        "error_key": "insufficient_balance",
                    },
                    status=400,
                )
            if str(exc) == "exchange_rate_missing":
                return JsonResponse(
                    {
                        "error": "No exchange rate exists for the selected date",
                        "error_key": "exchange_rate_missing",
                    },
                    status=400,
                )
            raise

        return JsonResponse(exp.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class ExpenseDetailView(View):
    def put(self, request, pk):
        data = json.loads(request.body)
        from core.services import ExpenseService
        try:
            exp = ExpenseService.update_expense(pk, data)
        except ValueError as exc:
            if str(exc) == "bank_account_required":
                return JsonResponse(
                    {
                        "error": "Bank account is required for this payment method",
                        "error_key": "bank_account_required",
                    },
                    status=400,
                )
            if str(exc) == "matching_balance_entry_not_found":
                return JsonResponse(
                    {
                        "error": "Matching balance entry not found",
                        "error_key": "matching_balance_not_found",
                    },
                    status=400,
                )
            if str(exc) == "insufficient_balance":
                return JsonResponse(
                    {
                        "error": "insufficient_balance",
                        "error_key": "insufficient_balance",
                    },
                    status=400,
                )
            if str(exc) == "exchange_rate_missing":
                return JsonResponse(
                    {
                        "error": "No exchange rate exists for the selected date",
                        "error_key": "exchange_rate_missing",
                    },
                    status=400,
                )
            raise

        return JsonResponse(exp.to_dict())

    def delete(self, request, pk):
        from core.services import ExpenseService
        try:
            ExpenseService.delete_expense(pk)
        except ValueError as exc:
            if str(exc) == "matching_balance_entry_not_found":
                return JsonResponse(
                    {
                        "error": "Matching balance entry not found",
                        "error_key": "matching_balance_not_found",
                    },
                    status=400,
                )
            raise

        return JsonResponse({"deleted": pk})
