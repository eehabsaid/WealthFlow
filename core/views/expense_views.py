# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from core.models import (
    SalaryEntry,
    BalanceEntry,
    ExpenseCategory,
    ExpenseSubcategory,
    Expense,
    BankCertificate,

)
from django.db.models import Q

import datetime
from core.services.balance.financial_sync_service import FinancialSyncService

User = get_user_model()

@method_decorator(csrf_exempt, name="dispatch")
class ExpenseCategoryListView(View):
    def get(self, request):
        cats = ExpenseCategory.objects.prefetch_related("subcategories").all()
        data = []
        for c in cats:
            d = c.to_dict()
            d["subcategories"] = [s.to_dict() for s in c.subcategories.all()]
            data.append(d)
        return JsonResponse({"categories": data})

    def post(self, request):
        data = json.loads(request.body)
        cat = ExpenseCategory.objects.create(
            name=data["name"],
            icon=data.get("icon", "💰"),
            color_hex=data.get("color_hex", "#0d6efd"),
            order=data.get("order", 0),
        )
        return JsonResponse(cat.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class ExpenseCategoryDetailView(View):
    def put(self, request, pk):
        cat = get_object_or_404(ExpenseCategory, pk=pk)
        data = json.loads(request.body)
        for f in ["name", "icon", "color_hex", "order"]:
            if f in data:
                setattr(cat, f, data[f])
        cat.save()
        return JsonResponse(cat.to_dict())

    def delete(self, request, pk):
        cat = get_object_or_404(ExpenseCategory, pk=pk)
        cat.delete()
        return JsonResponse({"deleted": pk})

@method_decorator(csrf_exempt, name="dispatch")
class ExpenseSubcategoryListView(View):
    def post(self, request):
        data = json.loads(request.body)
        sub = ExpenseSubcategory.objects.create(
            category_id=data["category_id"],
            name=data["name"],
            order=data.get("order", 0),
        )
        return JsonResponse(sub.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class ExpenseSubcategoryDetailView(View):
    def put(self, request, pk):
        sub = get_object_or_404(ExpenseSubcategory, pk=pk)
        data = json.loads(request.body)
        for f in ["name", "order"]:
            if f in data:
                setattr(sub, f, data[f])
        sub.save()
        return JsonResponse(sub.to_dict())

    def delete(self, request, pk):
        sub = get_object_or_404(ExpenseSubcategory, pk=pk)
        sub.delete()
        return JsonResponse({"deleted": pk})

def _normalize_expense_payment_method(method_value):
    method = str(method_value or "").strip().lower()
    if method == "cash":
        return "cash"
    if method in {"bank", "bank transfer", "bank_transfer"}:
        return "bank"
    if method == "card":
        return "card"
    return method

def _expense_requires_bank(method_value):
    return _normalize_expense_payment_method(method_value) in {"bank", "card"}

def _expense_affects_balance(method_value):
    return _normalize_expense_payment_method(method_value) in {"cash", "bank", "card"}

def _get_target_cash_balance_entry(payment_method, bank_id):
    qs = BalanceEntry.objects.select_for_update().filter(
        balance_type=BalanceEntry.BalanceType.CASH,
    )
    egp_or_cash_qs = qs.filter(
        Q(currency__code__iexact="EGP")
        | Q(currency__code__iexact="CASH")
        | Q(currency__name__iexact="Cash")
    )
    if egp_or_cash_qs.exists():
        qs = egp_or_cash_qs

    normalized_method = _normalize_expense_payment_method(payment_method)
    if normalized_method == "cash":
        qs = qs.filter(bank__isnull=True)
    else:
        qs = qs.filter(bank_id=bank_id)

    return qs.order_by("id").first()

def _apply_expense_balance_delta(payment_method, bank_id, amount_delta):
    if not _expense_affects_balance(payment_method):
        return

    delta = Decimal(str(amount_delta or 0))
    if delta == 0:
        return

    entry = _get_target_cash_balance_entry(payment_method, bank_id)
    if not entry:
        raise ValueError("matching_balance_entry_not_found")

    if delta < 0 and (Decimal(entry.amount or 0) + delta) < 0:
        raise ValueError("insufficient_balance")

    entry.amount = Decimal(entry.amount or 0) + delta
    entry.save(update_fields=["amount"])

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

@method_decorator(csrf_exempt, name="dispatch")
class ExpenseSummaryView(View):
    """Returns monthly totals + category breakdown for charts."""

    def get(self, request):
        import calendar

        year = request.GET.get("year")
        month = request.GET.get("month")
        qs = Expense.objects.all()
        if year:
            qs = qs.filter(year=int(year))
        if month:
            qs = qs.filter(month=int(month))

        # By category
        by_cat = {}
        for e in qs.select_related("category"):
            name = e.category.name if e.category else "Uncategorised"
            icon = e.category.icon if e.category else "💰"
            color = e.category.color_hex if e.category else "#6c757d"
            key = name
            if key not in by_cat:
                by_cat[key] = {"name": name, "icon": icon, "color": color, "total": 0}
            by_cat[key]["total"] += float(e.amount_egp)

        # Monthly trend (last 12 months)
        monthly = []
        for m in range(1, 13):
            y = int(year) if year else datetime.date.today().year
            total = (
                Expense.objects.filter(year=y, month=m).aggregate(t=Sum("amount_egp"))["t"]
                or 0
            )
            monthly.append({"month": m, "total": float(total)})

        grand_total = sum(v["total"] for v in by_cat.values())

        # Income summary for reports (salary + certificate interest)
        month_names = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ]

        def _month_bounds(y, m):
            start = datetime.date(y, m, 1)
            end = datetime.date(y, m, calendar.monthrange(y, m)[1])
            return start, end

        def _year_bounds(y):
            return datetime.date(y, 1, 1), datetime.date(y, 12, 31)

        def _includes_in_period(certificate, start_date, end_date):
            if not certificate:
                return False
            issue_date = certificate.issue_date
            expiry_date = certificate.expiry_date
            if issue_date and issue_date > end_date:
                return False
            if expiry_date and expiry_date < start_date:
                return False
            return True

        salary_amount = 0.0
        total_interest = 0.0
        rental_income = 0.0

        if month:
            target_year = int(year) if year else datetime.date.today().year
            target_month = int(month)
            prev_month = target_month - 1
            prev_year = target_year
            if prev_month == 0:
                prev_month = 12
                prev_year -= 1

            prev_month_name = month_names[prev_month - 1]
            salary_qs = SalaryEntry.objects.filter(
                year=prev_year,
                month__iexact=prev_month_name,
            )
            salary_amount = float(
                salary_qs.aggregate(total=Sum("paid"))["total"] or 0
            )

            start_date, end_date = _month_bounds(target_year, target_month)
            certs = BankCertificate.objects.all()
            total_interest = sum(
                float(c.interest_value or 0)
                for c in certs
                if _includes_in_period(c, start_date, end_date)
            )
            rental_income = float(FinancialSyncService().period_rental_income_total("month"))
        elif year:
            salary_amount = float(
                SalaryEntry.objects.filter(year=int(year)).aggregate(total=Sum("paid"))["total"]
                or 0
            )
            start_date, end_date = _year_bounds(int(year))
            certs = BankCertificate.objects.all()
            total_interest = sum(
                float(c.interest_value or 0)
                for c in certs
                if _includes_in_period(c, start_date, end_date)
            )
            rental_income = float(FinancialSyncService().period_rental_income_total("year"))
        else:
            today = datetime.date.today()
            start_date, end_date = _month_bounds(today.year, today.month)
            salary_amount = 0.0
            total_interest = sum(
                float(c.interest_value or 0)
                for c in BankCertificate.objects.all()
                if _includes_in_period(c, start_date, end_date)
            )
            rental_income = float(FinancialSyncService().period_rental_income_total("month"))

        total_income = salary_amount + total_interest + rental_income

        return JsonResponse(
            {
                "by_category": list(by_cat.values()),
                "monthly_trend": monthly,
                "grand_total": grand_total,
                "income_summary": {
                    "total_income": total_income,
                    "total_salary": salary_amount,
                    "total_interest": total_interest,
                    "total_rental_income": rental_income,
                },
            }
        )

