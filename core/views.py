import json
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db.models import Sum, Count
from django.shortcuts import render, get_object_or_404, redirect
from .models import (
    Company,
    SalaryEntry,
    Bank,
    BalanceEntry,
    AppSettings,
    ExchangeRate,
    GoldPrice,
    Currency,
    ExpenseCategory,
    ExpenseSubcategory,
    Expense,
    BankCertificate,
    PagePermission,
    PAGE_PERMISSION_CHOICES,
    UserProfile,
    ReminderRule,
    CertificateStatus,
    ReminderLog,
    REMINDER_TYPE_CHOICES,
    SALARY_TRIGGER_CHOICES,
)
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from django.http import HttpResponse

import json as _json
import datetime
import os
import io
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from arabic_reshaper import reshape
from bidi.algorithm import get_display


@method_decorator(csrf_exempt, name="dispatch")
class ExportExcelWorkbookView(View):
    """
    Generates a multi-tab Excel Workbook from live DB data,
    matching the original Balance.xlsx format, styles, and formulas,
    with an added Expenses tab.
    """

    def get(self, request):
        return self.post(request)

    def post(self, request):
        from .excel_export import generate_excel
        from datetime import date

        buf = generate_excel()
        filename = f"Balance_Tracker_{date.today().strftime('%Y%m%d')}.xlsx"
        response = HttpResponse(
            buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


User = get_user_model()

PAGE_PERMISSION_KEYS = [key for key, _ in PAGE_PERMISSION_CHOICES]

# Month sort order — ensures API returns months in calendar order, not alphabetically
MONTH_ORDER = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
    "Quarter-Bonuses",
]


def month_sort_key(entry_dict):
    try:
        return MONTH_ORDER.index(entry_dict.get("month", ""))
    except ValueError:
        return len(MONTH_ORDER)


@login_required(login_url="/accounts/login/")
def index(request):
    return render(request, "index.html")


def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return JsonResponse({"error": "Admin access required"}, status=403)


def _build_user_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


def _get_user_allowed_pages(user):
    return [perm.page for perm in user.page_permissions.all()]


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("/")
        return render(request, "login.html", {"error": "Invalid username or password"})
    return render(request, "login.html")


def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not username or not email or not password:
            return render(request, "signup.html", {"error": "All fields are required"})
        if password != confirm_password:
            return render(request, "signup.html", {"error": "Passwords do not match"})
        if User.objects.filter(username=username).exists():
            return render(
                request, "signup.html", {"error": "Username is already taken"}
            )
        if User.objects.filter(email=email).exists():
            return render(
                request, "signup.html", {"error": "Email is already registered"}
            )

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        login(request, user)
        return redirect("/")

    return render(request, "signup.html")


def logout_view(request):
    logout(request)
    return redirect("/accounts/login/")


class LoginAPIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        username = data.get("username", "").strip()
        password = data.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({"error": "Invalid credentials"}, status=400)
        login(request, user)
        return JsonResponse(
            {
                "user": _build_user_dict(user),
                "allowed_pages": _get_user_allowed_pages(user),
            }
        )


class SignupAPIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")

        if not username or not email or not password:
            return JsonResponse(
                {"error": "Username, email and password are required"}, status=400
            )
        if password != confirm_password:
            return JsonResponse({"error": "Passwords do not match"}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username is already taken"}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({"error": "Email is already registered"}, status=400)

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        login(request, user)
        return JsonResponse(
            {
                "user": _build_user_dict(user),
                "allowed_pages": _get_user_allowed_pages(user),
            }
        )


class LogoutAPIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        logout(request)
        return JsonResponse({"success": True})


class CurrentUserView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"user": None, "allowed_pages": []})
        return JsonResponse(
            {
                "user": _build_user_dict(request.user),
                "allowed_pages": _get_user_allowed_pages(request.user),
            }
        )


class UserListView(AdminRequiredMixin, View):
    def get(self, request):
        # support pagination and search: ?page=1&page_size=20&q=term
        q = request.GET.get("q", "").strip()
        page = int(request.GET.get("page", 1) or 1)
        page_size = int(request.GET.get("page_size", 20) or 20)

        qs = User.objects.order_by("username").all()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))

        paginator = Paginator(qs, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        users = [_build_user_dict(u) for u in page_obj.object_list]
        return JsonResponse(
            {
                "users": users,
                "page": page_obj.number,
                "page_size": page_size,
                "total": paginator.count,
                "num_pages": paginator.num_pages,
            }
        )

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")
        if not username or not email or not password:
            return JsonResponse(
                {"error": "username, email and password are required"}, status=400
            )
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username is already taken"}, status=400)
        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        user.is_active = data.get("is_active", True)
        user.is_staff = data.get("is_staff", False)
        user.is_superuser = data.get("is_superuser", False)
        user.save()
        return JsonResponse({"user": _build_user_dict(user)}, status=201)


class UserDetailView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return JsonResponse({"user": _build_user_dict(user)})

    def put(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        for field in ["email", "is_active", "is_staff", "is_superuser"]:
            if field in data:
                setattr(user, field, data[field])
        if data.get("password"):
            user.set_password(data["password"])
        user.save()
        return JsonResponse({"user": _build_user_dict(user)})

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.delete()
        return JsonResponse({"deleted": pk})


class UserPermissionListView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        permissions = user.page_permissions.all()
        return JsonResponse(
            {
                "permissions": [perm.to_dict() for perm in permissions],
                "available_pages": PAGE_PERMISSION_CHOICES,
            }
        )

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        page = data.get("page")
        if page not in PAGE_PERMISSION_KEYS:
            return JsonResponse({"error": "Invalid page permission"}, status=400)
        perm, created = PagePermission.objects.get_or_create(user=user, page=page)
        return JsonResponse(
            {"permission": perm.to_dict()}, status=201 if created else 200
        )


class UserBulkActionView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        action = data.get("action")
        ids = data.get("ids") or []
        if not action or not isinstance(ids, list):
            return JsonResponse({"error": "action and ids required"}, status=400)

        users = User.objects.filter(id__in=ids)
        changed = 0
        if action == "delete":
            changed = users.count()
            users.delete()
        elif action == "activate":
            changed = users.update(is_active=True)
        elif action == "deactivate":
            changed = users.update(is_active=False)
        elif action == "set_staff":
            val = bool(data.get("value"))
            changed = users.update(is_staff=val)
        elif action == "set_superuser":
            val = bool(data.get("value"))
            changed = users.update(is_superuser=val)
        else:
            return JsonResponse({"error": "unknown action"}, status=400)

        return JsonResponse({"changed": changed})


class UserPermissionDetailView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, pk):
        perm = get_object_or_404(PagePermission, pk=pk)
        perm.delete()
        return JsonResponse({"deleted": pk})


class PagePermissionChoicesView(AdminRequiredMixin, View):
    def get(self, request):
        return JsonResponse({"available_pages": PAGE_PERMISSION_CHOICES})


@login_required(login_url="/accounts/login/")
def user_management_page(request):
    # Only staff (admins) can access the management UI
    if not request.user.is_staff:
        return redirect("/")
    return render(request, "user_management.html")


@method_decorator(csrf_exempt, name="dispatch")
class CompanyListView(View):
    def get(self, request):
        companies = Company.objects.all().order_by("order")
        return JsonResponse({"companies": [c.to_dict() for c in companies]})

    def post(self, request):
        data = json.loads(request.body)
        company = Company.objects.create(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            group_name=data.get("group_name", ""),
            color_hex=data.get("color_hex", "#0d6efd"),
            is_active=data.get("is_active", True),
            order=data.get("order", 0),
        )
        return JsonResponse(company.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class CompanyDetailView(View):
    def get(self, request, pk):
        c = get_object_or_404(Company, pk=pk)
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
        ]:
            if field in data:
                setattr(c, field, data[field])
        c.save()
        return JsonResponse(c.to_dict())

    def delete(self, request, pk):
        c = get_object_or_404(Company, pk=pk)
        c.delete()
        return JsonResponse({"deleted": pk})


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
        entry = get_object_or_404(SalaryEntry, pk=pk)
        data = json.loads(request.body)
        for field in ["year", "month", "expected", "paid", "bonus", "notes"]:
            if field in data:
                setattr(entry, field, data[field])
        entry.save()
        return JsonResponse(entry.to_dict())

    def delete(self, request, pk):
        entry = get_object_or_404(SalaryEntry, pk=pk)
        entry.delete()
        return JsonResponse({"deleted": pk})


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
class BankListView(View):
    def get(self, request):
        return JsonResponse({"banks": [b.to_dict() for b in Bank.objects.all()]})

    def post(self, request):
        data = json.loads(request.body)
        bank = Bank.objects.create(
            name=data["name"],
            account_number=data.get("account_number", ""),
            card_id=data.get("card_id", ""),
            swift_code=data.get("swift_code", ""),
            customer_id=data.get("customer_id", ""),
            customer_name=data.get("customer_name", ""),
            is_active=data.get("is_active", True),
            order=data.get("order", 0),
        )
        return JsonResponse(bank.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class BankDetailView(View):
    def put(self, request, pk):
        bank = get_object_or_404(Bank, pk=pk)
        data = json.loads(request.body)
        for field in [
            "name",
            "account_number",
            "card_id",
            "swift_code",
            "customer_id",
            "customer_name",
            "is_active",
            "order",
        ]:
            if field in data:
                setattr(bank, field, data[field])
        bank.save()
        return JsonResponse(bank.to_dict())

    def delete(self, request, pk):
        bank = get_object_or_404(Bank, pk=pk)
        bank.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class BankCertificateListView(View):
    def get(self, request):
        certificates = BankCertificate.objects.select_related("bank", "currency").all()
        return JsonResponse({"certificates": [c.to_dict() for c in certificates]})

    def post(self, request):
        data = json.loads(request.body)
        certificate = BankCertificate.objects.create(
            bank_id=data["bank_id"],
            currency_id=data.get("currency_id"),
            issue_date=data.get("issue_date") or None,
            expiry_date=data.get("expiry_date") or None,
            amount=data.get("amount", 0),
            interest_rate=data.get("interest_rate", 0),
            interest_value=data.get("interest_value", 0),
            frequency=data.get("frequency", ""),
            status=data.get("status", "Active"),
            notes=data.get("notes", ""),
        )
        return JsonResponse(certificate.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class BankCertificateDetailView(View):
    def get(self, request, pk):
        certificate = get_object_or_404(BankCertificate, pk=pk)
        return JsonResponse(certificate.to_dict())

    def put(self, request, pk):
        certificate = get_object_or_404(BankCertificate, pk=pk)
        data = json.loads(request.body)
        for field in [
            "bank_id",
            "currency_id",
            "issue_date",
            "expiry_date",
            "amount",
            "interest_rate",
            "interest_value",
            "frequency",
            "status",
            "notes",
        ]:
            if field in data:
                setattr(certificate, field, data[field])
        certificate.save()
        return JsonResponse(certificate.to_dict())

    def delete(self, request, pk):
        certificate = get_object_or_404(BankCertificate, pk=pk)
        certificate.delete()
        return JsonResponse({"deleted": pk})

@method_decorator(csrf_exempt, name="dispatch")
class CurrencyListView(View):
    def get(self, request):
        currencies = Currency.objects.all().order_by("order")
        return JsonResponse({"currencies": [c.to_dict() for c in currencies]})

    def post(self, request):
        data = json.loads(request.body)
        currency = Currency.objects.create(
            code=data["code"],
            symbol=data.get("symbol", ""),
            flag=data.get("flag", "💱"),
            name=data.get("name", data["code"]),
            order=data.get("order", 0),
        )
        return JsonResponse(currency.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class CurrencyDetailView(View):
    def get(self, request, pk):
        c = get_object_or_404(Currency, pk=pk)
        return JsonResponse(c.to_dict())

    def put(self, request, pk):
        c = get_object_or_404(Currency, pk=pk)
        data = json.loads(request.body)
        for field in ["code", "symbol", "flag", "name", "order"]:
            if field in data:
                setattr(c, field, data[field])
        c.save()
        return JsonResponse(c.to_dict())

    def delete(self, request, pk):
        c = get_object_or_404(Currency, pk=pk)
        c.delete()
        return JsonResponse({"deleted": pk})

@method_decorator(csrf_exempt, name="dispatch")
class BalanceListView(View):
    def get(self, request):
        entries = BalanceEntry.objects.select_related("bank", "currency").all()
        return JsonResponse({"entries": [e.to_dict() for e in entries]})

    def post(self, request):
        data = json.loads(request.body)
        entry = BalanceEntry.objects.create(
            title=data["title"],
            balance_type=data["balance_type"],
            bank_id=data.get("bank_id"),
            currency_id=data.get("currency_id", 1),
            amount=data.get("amount", 0),
            notes=data.get("notes", ""),
        )
        return JsonResponse(entry.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class BalanceDetailView(View):
    def put(self, request, pk):
        entry = get_object_or_404(BalanceEntry, pk=pk)
        data = json.loads(request.body)
        for field in ["title", "balance_type", "bank_id", "currency_id", "amount", "notes"]:
            if field in data:
                setattr(entry, field, data[field])
        entry.save()
        return JsonResponse(entry.to_dict())

    def delete(self, request, pk):
        entry = get_object_or_404(BalanceEntry, pk=pk)
        entry.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class SettingsView(View):
    def get(self, request):
        settings = AppSettings.objects.all()
        return JsonResponse({"settings": {s.key: s.value for s in settings}})

    def post(self, request):
        data = json.loads(request.body)
        obj = AppSettings.set(data["key"], data["value"])
        return JsonResponse({"key": obj.key, "value": obj.value})


# ── Exchange Rates views ──────────────────────────────────────


@method_decorator(csrf_exempt, name="dispatch")
class ExchangeRateListView(View):
    """GET  /api/rates/          → latest rate per currency
    POST /api/rates/refresh/  → fetch from internet and save"""

    def get(self, request):
        """Return the single most-recent row per currency code."""
        from django.db.models import Max

        latest_ids = (
            ExchangeRate.objects.values("currency_code")
            .annotate(max_id=Max("id"))
            .values_list("max_id", flat=True)
        )
        rates = ExchangeRate.objects.filter(id__in=latest_ids).order_by("currency_code")
        last = ExchangeRate.objects.order_by("-fetched_at").first()
        return JsonResponse(
            {
                "rates": [r.to_dict() for r in rates],
                "fetched_at": (
                    last.fetched_at.strftime("%Y-%m-%d %H:%M") if last else None
                ),
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class ExchangeRateRefreshView(View):
    """Calls open.er-api.com and saves latest rates to DB."""

    def post(self, request):
        import urllib.request as _ur
        import json as _json
        import decimal

        CURRENCY_NAMES = {
            "USD": "US Dollar",
            "EUR": "Euro",
            "GBP": "Pound Sterling",
            "SAR": "Saudi Riyal",
            "AED": "UAE Dirham",
            "KWD": "Kuwaiti Dinar",
            "CAD": "Canadian Dollar",
            "CHF": "Swiss Franc",
            "JPY": "Japanese Yen",
            "CNY": "Chinese Yuan",
            "QAR": "Qatari Riyal",
            "BHD": "Bahraini Dinar",
            "OMR": "Omani Riyal",
            "JOD": "Jordanian Dinar",
            "NOK": "Norwegian Krone",
            "SEK": "Swedish Krona",
            "DKK": "Danish Krone",
            "AUD": "Australian Dollar",
        }

        try:
            url = "https://open.er-api.com/v6/latest/EGP"
            req = _ur.Request(url, headers={"User-Agent": "SalaryTracker/1.0"})
            with _ur.urlopen(req, timeout=15) as resp:
                data = _json.loads(resp.read().decode())

            if data.get("result") != "success":
                return JsonResponse({"error": "API returned non-success"}, status=502)

            rates_raw = data.get("rates", {})  # all rates are X per 1 EGP
            saved = 0
            with transaction.atomic():
                ExchangeRate.objects.all().delete()
                for code, name in CURRENCY_NAMES.items():
                    if code not in rates_raw:
                        continue
                    # rates_raw[code] = how many <code> per 1 EGP
                    # We want EGP per 1 <code>  (buy rate)
                    egp_per_unit = (
                        1.0 / float(rates_raw[code]) if float(rates_raw[code]) else 0
                    )
                    # Apply a typical 0.5% spread for buy/sell simulation
                    spread = egp_per_unit * 0.005
                    ExchangeRate.objects.create(
                        currency_code=code,
                        currency_name=name,
                        buy_rate=round(egp_per_unit - spread, 6),
                        sell_rate=round(egp_per_unit + spread, 6),
                        mid_rate=round(egp_per_unit, 6),
                        source="open.er-api.com",
                    )
                    saved += 1

            return JsonResponse(
                {"saved": saved, "message": f"Fetched {saved} currencies"}
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=502)


# ── Gold Price views ──────────────────────────────────────────


@method_decorator(csrf_exempt, name="dispatch")
class GoldPriceListView(View):
    """GET /api/gold/ → latest gold price"""

    def get(self, request):
        latest = GoldPrice.objects.order_by("-fetched_at").first()
        if not latest:
            return JsonResponse(
                {"gold": None, "message": "No data yet. Click Refresh."}
            )
        return JsonResponse({"gold": latest.to_dict()})


@method_decorator(csrf_exempt, name="dispatch")
class GoldPriceRefreshView(View):
    """Fetches EGP gold prices from goldbullioneg.com and USD/EGP from open.er-api.com."""

    def get(self, request):
        return self.post(request)

    def post(self, request):
        import urllib.request as _ur
        import json as _json
        from html.parser import HTMLParser
        import re

        class GoldTableParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_table = False
                self.in_tr = False
                self.in_td = False
                self.current_cell = None
                self.current_row = []
                self.rows = []

            def handle_starttag(self, tag, attrs):
                if tag == "table" and not self.in_table:
                    self.in_table = True
                    return
                if not self.in_table:
                    return
                if tag == "tr":
                    self.in_tr = True
                    self.current_row = []
                elif self.in_tr and tag == "td":
                    self.in_td = True
                    self.current_cell = {"text": "", "data_val": None}
                    attrs = dict(attrs)
                    if "data-val" in attrs:
                        self.current_cell["data_val"] = attrs["data-val"]

            def handle_data(self, data):
                if self.in_td and self.current_cell is not None:
                    self.current_cell["text"] += data

            def handle_endtag(self, tag):
                if tag == "td" and self.in_td:
                    self.current_row.append(self.current_cell)
                    self.in_td = False
                    self.current_cell = None
                elif tag == "tr" and self.in_tr:
                    if self.current_row:
                        self.rows.append(self.current_row)
                    self.in_tr = False
                elif tag == "table" and self.in_table:
                    self.in_table = False

        try:
            import ssl as _ssl

            # goldbullioneg.com has an expired SSL cert — bypass verification for this trusted source
            _ctx = _ssl.create_default_context()
            _ctx.check_hostname = False
            _ctx.verify_mode = _ssl.CERT_NONE

            # Step 1: Scrape gold prices directly from goldbullioneg.com (EGP table)
            page_url = "https://goldbullioneg.com/%D8%A3%D8%B3%D8%B9%D8%A7%D8%B1-%D8%A7%D9%84%D8%B0%D9%87%D8%A8/"
            req = _ur.Request(page_url, headers={"User-Agent": "SalaryTracker/1.0"})
            with _ur.urlopen(req, timeout=15, context=_ctx) as resp:
                page_html = resp.read().decode("utf-8", errors="ignore")

            parser = GoldTableParser()
            parser.feed(page_html)

            if not parser.rows or len(parser.rows) < 8:
                return JsonResponse(
                    {
                        "error": "Unable to parse complete gold price table from goldbullioneg.com"
                    },
                    status=502,
                )

            prices_egp = {}  # {carat: {'buy': X, 'sell': Y}}
            usd_to_egp = None
            usd_per_oz = None

            for idx, row in enumerate(parser.rows):
                if len(row) < 3:
                    continue
                label = (row[0]["text"] or "").strip()
                buy_val = (row[1]["data_val"] or row[1]["text"] or "").strip()
                sell_val = (row[2]["data_val"] or row[2]["text"] or "").strip()

                if not buy_val or not sell_val:
                    continue

                try:
                    buy_num = float(buy_val.replace(",", ""))
                    sell_num = float(sell_val.replace(",", ""))
                except ValueError:
                    continue

                # Check for karat prices (جرام عيار X)
                karat_match = re.search(r"عيار\s*([0-9]{1,2})", label)
                if karat_match:
                    carat = int(karat_match.group(1))
                    prices_egp[carat] = {"buy": buy_num, "sell": sell_num}
                    continue

                # Check for USD/EGP rate (الدولار)
                if "دولار" in label.lower():
                    usd_to_egp = sell_num
                    continue

                # Check for USD spot price per ounce (الأونصة)
                if "أونصة" in label.lower() or "ounce" in label.lower():
                    usd_per_oz = sell_num
                    continue

            if not all(k in prices_egp for k in (24, 22, 21, 18)):
                return JsonResponse(
                    {"error": "Missing required karat prices from goldbullioneg.com"},
                    status=502,
                )

            if usd_to_egp is None:
                return JsonResponse(
                    {"error": "Could not find USD/EGP rate on goldbullioneg.com"},
                    status=502,
                )

            if usd_per_oz is None:
                return JsonResponse(
                    {"error": "Could not find USD/oz spot price on goldbullioneg.com"},
                    status=502,
                )

            # Calculate USD per gram from the EGP per gram (using sell price)
            usd_gram_24k = prices_egp[24]["sell"] / usd_to_egp if usd_to_egp else 0

            with transaction.atomic():
                GoldPrice.objects.all().delete()
                gp = GoldPrice.objects.create(
                    carat_24k=round(prices_egp[24]["sell"], 2),
                    carat_22k=round(prices_egp[22]["sell"], 2),
                    carat_21k=round(prices_egp[21]["sell"], 2),
                    carat_18k=round(prices_egp[18]["sell"], 2),
                    carat_24k_buy=round(prices_egp[24]["buy"], 2),
                    carat_22k_buy=round(prices_egp[22]["buy"], 2),
                    carat_21k_buy=round(prices_egp[21]["buy"], 2),
                    carat_18k_buy=round(prices_egp[18]["buy"], 2),
                    usd_gram_24k=round(usd_gram_24k, 6),
                    usd_per_oz=round(usd_per_oz, 4),
                    usd_to_egp=round(usd_to_egp, 6),
                    source_gold="goldbullioneg.com",
                    source_fx="goldbullioneg.com",
                )
            return JsonResponse({"gold": gp.to_dict()})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=502)


# ══════════════════════════════════════════════════════════════
# EXPENSE VIEWS
# ══════════════════════════════════════════════════════════════


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


@method_decorator(csrf_exempt, name="dispatch")
class ExpenseListView(View):
    def get(self, request):
        qs = Expense.objects.select_related("category", "subcategory", "currency").all()

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

        total = sum(float(e["amount"] or 0) for e in entries)

        return JsonResponse({"entries": entries, "total": total})

    def post(self, request):
        data = json.loads(request.body)
        from datetime import date as _date

        d = _date.fromisoformat(data["date"])
        exp = Expense.objects.create(
            date=d,
            year=d.year,
            month=d.month,
            category_id=data.get("category_id"),
            subcategory_id=data.get("subcategory_id"),
            description=data.get("description", ""),
            amount=data.get("amount", 0),
            currency_id=data.get("currency_id"),
            payment_method=data.get("payment_method", "Cash"),
            notes=data.get("notes", ""),
        )
        return JsonResponse(exp.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class ExpenseDetailView(View):
    def put(self, request, pk):
        exp = get_object_or_404(Expense, pk=pk)
        data = json.loads(request.body)
        if "date" in data:
            from datetime import date as _date

            d = _date.fromisoformat(data["date"])
            exp.date = d
            exp.year = d.year
            exp.month = d.month
        for f in [
            "category_id",
            "subcategory_id",
            "description",
            "amount",
            "currency_id",
            "payment_method",
            "notes",
        ]:
            if f in data:
                setattr(exp, f, data[f])
        exp.save()
        return JsonResponse(exp.to_dict())

    def delete(self, request, pk):
        exp = get_object_or_404(Expense, pk=pk)
        exp.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class ExpenseSummaryView(View):
    """Returns monthly totals + category breakdown for charts."""

    def get(self, request):
        from django.db.models import Sum

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
            by_cat[key]["total"] += float(e.amount)

        # Monthly trend (last 12 months)
        from django.db.models.functions import TruncMonth
        import datetime

        monthly = []
        for m in range(1, 13):
            y = int(year) if year else datetime.date.today().year
            total = (
                Expense.objects.filter(year=y, month=m).aggregate(t=Sum("amount"))["t"]
                or 0
            )
            monthly.append({"month": m, "total": float(total)})

        grand_total = sum(v["total"] for v in by_cat.values())
        return JsonResponse(
            {
                "by_category": list(by_cat.values()),
                "monthly_trend": monthly,
                "grand_total": grand_total,
            }
        )


# ══════════════════════════════════════════════════════════════
# PDF REPORT VIEW
# ══════════════════════════════════════════════════════════════
# Helper to load translations
def get_translations(lang):
    path = os.path.join(settings.BASE_DIR, "static", "i18n", f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {}


def format_arabic(text):
    return get_display(reshape(str(text)))


def get_text(key, lang, t, default=""):
    text = t.get(key, default)
    return format_arabic(text) if lang == "ar" else text


@method_decorator(csrf_exempt, name="dispatch")
class GenerateReportView(View):
    """
    POST /api/reports/generate/
    body: { type: "monthly"|"yearly"|"custom",
            year: 2026, month: 5,       # for monthly
            start_date: "2026-01-01",   # for custom
            end_date:   "2026-05-31" }
    Returns: PDF file
    """

    def post(self, request):
        import json as _json, datetime
        from django.http import HttpResponse, JsonResponse
        from django.db.models import Sum

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
                HRFlowable,
            )
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
            import io
        except ImportError:
            return JsonResponse(
                {"error": "reportlab not installed. Run: pip install reportlab"},
                status=500,
            )

        data = _json.loads(request.body)
        lang = data.get("lang", "en")
        t = get_translations(lang)

        # Register Arabic-compatible font if the file exists
        font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "arial.ttf")
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("ArabicFont", font_path))

        # Decide which font style template to use
        pdf_font = "ArabicFont" if lang == "ar" else "Helvetica-Bold"

        rtype = data.get("type", "monthly")
        year = int(data.get("year", datetime.date.today().year))
        month = int(data.get("month", datetime.date.today().month))

        # Accept both parameter styles (with or without suffix) to be fully secure
        start_date = data.get("start_date") or data.get("start")
        end_date = data.get("end_date") or data.get("end")

        # ── Filter expenses safely across all field schemas ──
        qs = Expense.objects.select_related("category", "subcategory").all()
        if rtype == "monthly":
            qs = qs.filter(year=year, month=month)
            month_name = datetime.date(year, month, 1).strftime("%B")
            json_month_key = f"month_{month_name.lower()}"
            translated_month = t.get(json_month_key)

            if not translated_month:
                if lang == "ar":
                    ARABIC_MONTHS = {
                        "January": "يناير",
                        "February": "فبراير",
                        "March": "مارس",
                        "April": "أبريل",
                        "May": "مايو",
                        "June": "يونيو",
                        "July": "يوليو",
                        "August": "أغسطس",
                        "September": "سبتمبر",
                        "October": "أكتوبر",
                        "November": "نوفمبر",
                        "December": "ديسمبر",
                    }
                    translated_month = ARABIC_MONTHS.get(month_name, month_name)
                else:
                    translated_month = month_name

            # FIXED: Changed long em-dash (—) to standard universal hyphen (-)
            title_str = f"{t.get('monthly_report', 'Monthly Report')} - {translated_month} {year}"
            filename = f"report_{year}_{month:02d}.pdf"
        elif rtype == "yearly":
            qs = qs.filter(year=year)
            # FIXED: Changed to standard hyphen
            title_str = f"{t.get('yearly_report', 'Yearly Report')} - {year}"
            filename = f"report_{year}.pdf"
        else:
            from datetime import date as _date

            sd = _date.fromisoformat(start_date)
            ed = _date.fromisoformat(end_date)
            qs = qs.filter(date__gte=sd, date__lte=ed)

            title_str = f"{t.get('report', 'Report')} {start_date} {t.get('to', 'to')} {end_date}"
            filename = f"report_{start_date}_{end_date}.pdf"

        if lang == "ar":
            title_str = format_arabic(title_str)

        expenses = list(qs)
        total_exp = sum(float(e.amount) for e in expenses)

        # Income for period (salary paid amounts)
        total_inc = 0
        if rtype == "monthly":
            # Target the previous month relative to the report month
            curr_date = datetime.date(year, month, 1)
            prev_date = curr_date - datetime.timedelta(days=1)
            sal_qs = SalaryEntry.objects.filter(
                year=prev_date.year, month=prev_date.strftime("%B")
            )
        elif rtype == "yearly":
            sal_qs = SalaryEntry.objects.filter(year=year)
        else:
            from datetime import date as _date

            sd = _date.fromisoformat(start_date)
            ed = _date.fromisoformat(end_date)

            MONTHS = [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ]

            sal_qs = SalaryEntry.objects.none()

            for year_num in range(sd.year, ed.year + 1):

                year_entries = SalaryEntry.objects.filter(year=year_num)

                for entry in year_entries:

                    try:

                        month_index = MONTHS.index(entry.month) + 1

                        entry_date = _date(year_num, month_index, 1)

                        if sd <= entry_date <= ed:

                            sal_qs |= SalaryEntry.objects.filter(pk=entry.pk)

                    except Exception:
                        pass

        total_inc += sum(float(s.paid or 0) for s in sal_qs)

        # 2. Add Bank Interest (Summing all certificates)
        total_interest = sum(
            float(c.interest_value or 0) for c in BankCertificate.objects.all()
        )
        # total_interest = 0
        total_inc += total_interest

        # 3. Final Calculations
        net_sav = total_inc - total_exp
        sav_rate = (net_sav / total_inc * 100) if total_inc > 0 else 0

        # Category breakdown
        cat_totals = {}
        for e in expenses:
            cname = e.category.name if e.category else "Uncategorised"
            cat_totals[cname] = cat_totals.get(cname, 0) + float(e.amount)

        # ── Build PDF ──
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        styles = getSampleStyleSheet()
        navy = colors.HexColor("#000080")
        blue = colors.HexColor("#1a6ef5")
        green = colors.HexColor("#00d68f")
        red = colors.HexColor("#ff4d6d")
        yellow = colors.HexColor("#ffd166")
        grey = colors.HexColor("#7b97cc")

        H1 = ParagraphStyle(
            "H1",
            fontSize=22,
            textColor=blue,
            spaceAfter=15,
            alignment=TA_CENTER,
            fontName=pdf_font,
        )
        H11 = ParagraphStyle(
            "H11",
            fontSize=18,
            textColor=navy,
            spaceAfter=15,
            alignment=TA_CENTER,
            fontName=pdf_font,
        )
        H2 = ParagraphStyle(
            "H2",
            fontSize=14,
            textColor=navy,
            spaceAfter=4,
            spaceBefore=12,
            fontName=pdf_font,
        )
        BODY = ParagraphStyle("BODY", fontSize=10, textColor=navy, spaceAfter=4)
        SUB = ParagraphStyle("SUB", fontSize=9, textColor=grey, spaceAfter=2)

        story = []

        # Cover
        story.append(Spacer(1, 1 * cm))

        # Fetch the clean, localized text without unstable emojis
        report_text = get_text("financial_report", lang, t, "Financial Report")

        # Append the titles cleanly to the story
        story.append(Paragraph(report_text, H1))
        story.append(Paragraph(title_str, H11))
        story.append(HRFlowable(width="100%", thickness=1, color=blue))
        story.append(Spacer(1, 0.5 * cm))
        # Dynamically set table title alignments based on the document language
        table_title_style = ParagraphStyle(
            "TableTitle", parent=H2, alignment=TA_RIGHT if lang == "ar" else TA_LEFT
        )
        # Summary KPIs
        story.append(
            Paragraph(get_text("summary", lang, t, "Summary"), table_title_style)
        )

        # Define explicit Paragraph styles for table cells to handle Arabic layout flawlessly
        cell_L = ParagraphStyle(
            "CellL", fontName=pdf_font, fontSize=10, textColor=navy, alignment=TA_LEFT
        )
        cell_R = ParagraphStyle(
            "CellR", fontName=pdf_font, fontSize=10, textColor=navy, alignment=TA_RIGHT
        )
        cell_HL = ParagraphStyle(
            "CellHL",
            fontName=pdf_font,
            fontSize=10,
            textColor=colors.white,
            alignment=TA_LEFT,
        )
        cell_HR = ParagraphStyle(
            "CellHR",
            fontName=pdf_font,
            fontSize=10,
            textColor=colors.white,
            alignment=TA_RIGHT,
        )

        kpi_data = [
            [
                Paragraph(get_text("metric", lang, t, "Metric"), cell_HL),
                Paragraph(get_text("amount", lang, t, "Amount (EGP)"), cell_HR),
            ],
            [
                Paragraph(get_text("total_income", lang, t, "Total Income"), cell_L),
                Paragraph(f"{total_inc:,.2f}", cell_R),
            ],
            [
                Paragraph(
                    get_text("total_expenses", lang, t, "Total Expenses"), cell_L
                ),
                Paragraph(f"{total_exp:,.2f}", cell_R),
            ],
            [
                Paragraph(get_text("net_savings", lang, t, "Net Savings"), cell_L),
                Paragraph(
                    f"{net_sav:,.2f}",
                    ParagraphStyle(
                        "NetSavR",
                        parent=cell_R,
                        textColor=green if net_sav >= 0 else red,
                    ),
                ),
            ],
            [
                Paragraph(get_text("savings_rate", lang, t, "Savings Rate"), cell_L),
                Paragraph(f"{sav_rate:.1f}%", cell_R),
            ],
        ]

        kpi_table = Table(kpi_data, colWidths=[9 * cm, 7 * cm])
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), blue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, -1), pdf_font),  # Applied globally
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.HexColor("#f0f4ff"), colors.white],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1e3a6e")),
                    ("PADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(kpi_table)
        story.append(Spacer(1, 0.5 * cm))

        # Category breakdown
        if cat_totals:
            story.append(
                Paragraph(
                    get_text("cat_breakdown", lang, t, "Expense Breakdown by Category"),
                    table_title_style,
                )
            )

            cell_L9 = ParagraphStyle(
                "CellL9",
                fontName=pdf_font,
                fontSize=9,
                textColor=navy,
                alignment=TA_LEFT,
            )
            cell_R9 = ParagraphStyle(
                "CellR9",
                fontName=pdf_font,
                fontSize=9,
                textColor=navy,
                alignment=TA_RIGHT,
            )
            cell_HL9 = ParagraphStyle(
                "CellHL9",
                fontName=pdf_font,
                fontSize=9,
                textColor=colors.white,
                alignment=TA_LEFT,
            )
            cell_HR9 = ParagraphStyle(
                "CellHR9",
                fontName=pdf_font,
                fontSize=9,
                textColor=colors.white,
                alignment=TA_RIGHT,
            )

            cat_data = [
                [
                    Paragraph(get_text("category", lang, t, "Category"), cell_HL9),
                    Paragraph(get_text("amount", lang, t, "Amount (EGP)"), cell_HR9),
                    Paragraph(get_text("pct", lang, t, "% of Total"), cell_HR9),
                ]
            ]

            for cname, ctotal in sorted(cat_totals.items(), key=lambda x: -x[1]):
                pct = (ctotal / total_exp * 100) if total_exp > 0 else 0
                # Reshape dynamic database category names if language is Arabic
                display_cname = format_arabic(cname) if lang == "ar" else cname

                cat_data.append(
                    [
                        Paragraph(display_cname, cell_L9),
                        Paragraph(f"{ctotal:,.2f}", cell_R9),
                        Paragraph(f"{pct:.1f}%", cell_R9),
                    ]
                )

            cat_data.append(
                [
                    Paragraph(get_text("total", lang, t, "TOTAL"), cell_L9),
                    Paragraph(f"{total_exp:,.2f}", cell_R9),
                    Paragraph("100%", cell_R9),
                ]
            )

            cat_table = Table(cat_data, colWidths=[9 * cm, 5 * cm, 3 * cm])
            cat_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), blue),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        (
                            "FONTNAME",
                            (0, 0),
                            (-1, -1),
                            pdf_font,
                        ),  # Fixed range to cover all cells
                        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0fe")),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -2),
                            [colors.HexColor("#f0f4ff"), colors.white],
                        ),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1e3a6e")),
                        ("PADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(cat_table)
            story.append(Spacer(1, 0.5 * cm))

        # Detailed expense entries
        if expenses:
            story.append(
                Paragraph(
                    get_text("expense_entries", lang, t, "Expense Entries"),
                    table_title_style,
                )
            )

            cell_L8 = ParagraphStyle(
                "CellL8",
                fontName=pdf_font,
                fontSize=8,
                textColor=navy,
                alignment=TA_LEFT,
            )
            cell_R8 = ParagraphStyle(
                "CellR8",
                fontName=pdf_font,
                fontSize=8,
                textColor=navy,
                alignment=TA_RIGHT,
            )
            cell_HL8 = ParagraphStyle(
                "CellHL8",
                fontName=pdf_font,
                fontSize=8,
                textColor=colors.white,
                alignment=TA_LEFT,
            )
            cell_HR8 = ParagraphStyle(
                "CellHR8",
                fontName=pdf_font,
                fontSize=8,
                textColor=colors.white,
                alignment=TA_RIGHT,
            )

            exp_data = [
                [
                    Paragraph(get_text("date", lang, t, "Date"), cell_HL8),
                    Paragraph(get_text("category", lang, t, "Category"), cell_HL8),
                    Paragraph(
                        get_text("description", lang, t, "Description"), cell_HL8
                    ),
                    Paragraph(get_text("method", lang, t, "Method"), cell_HL8),
                    Paragraph(get_text("amount", lang, t, "Amount"), cell_HR8),
                ]
            ]

            for e in sorted(expenses, key=lambda x: x.date):
                cname = e.category.name if e.category else "—"
                desc = e.description or "—"
                method = e.payment_method or "—"

                # Reshape dynamic Arabic inputs from the database if active language is Arabic
                if lang == "ar":
                    cname = format_arabic(cname)
                    desc = format_arabic(desc[:40])
                    method = format_arabic(method)
                else:
                    desc = desc[:40]

                exp_data.append(
                    [
                        Paragraph(e.date.strftime("%d/%m/%Y"), cell_L8),
                        Paragraph(cname, cell_L8),
                        Paragraph(desc, cell_L8),
                        Paragraph(method, cell_L8),
                        Paragraph(f"{float(e.amount):,.2f}", cell_R8),
                    ]
                )

            exp_table = Table(
                exp_data, colWidths=[2.5 * cm, 3.5 * cm, 6 * cm, 3 * cm, 3 * cm]
            )
            exp_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), blue),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        (
                            "FONTNAME",
                            (0, 0),
                            (-1, -1),
                            pdf_font,
                        ),  # Fixed range to cover all cells
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.HexColor("#f0f4ff"), colors.white],
                        ),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#1e3a6e")),
                        ("PADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(exp_table)

        # Footer
        story.append(Spacer(1, 1 * cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=grey))

        # 1. Extract current date components
        today = datetime.date.today()
        f_day = today.day
        f_year = today.year
        f_month_name = today.strftime("%B")  # e.g., "June"

        # 2. Look up the translation key across ALL languages matching the header logic
        f_json_key = f"month_{f_month_name.lower()}"
        f_translated_month = t.get(f_json_key)

        # Fallback handling if a language JSON file is missing the specific month key
        if not f_translated_month:
            if lang == "ar":
                ARABIC_MONTHS = {
                    "January": "يناير",
                    "February": "فبراير",
                    "March": "مارس",
                    "April": "أبريل",
                    "May": "مايو",
                    "June": "يونيو",
                    "July": "يوليو",
                    "August": "أغسطس",
                    "September": "سبتمبر",
                    "October": "أكتوبر",
                    "November": "نوفمبر",
                    "December": "ديسمبر",
                }
                f_translated_month = ARABIC_MONTHS.get(f_month_name, f_month_name)
            else:
                f_translated_month = f_month_name

        # 3. Pull the "generated_by" label from the translation context
        raw_label = t.get("generated_by", "Generated by Salary & Balance Tracker")

        # 4. Construct layout string based on text direction rules
        if lang == "ar":
            # Combined with a standard hyphen, then reshaped once safely
            raw_footer = f"{raw_label} - {f_day} {f_translated_month} {f_year}"
            footer_text = format_arabic(raw_footer)
        else:
            # Handles English, French, and all other LTR languages uniformly
            footer_text = f"{raw_label} - {f_day} {f_translated_month} {f_year}"

        # 5. Append the translated paragraph to the layout story
        story.append(
            Paragraph(
                footer_text,
                ParagraphStyle(
                    "F",
                    fontSize=8,
                    textColor=grey,
                    alignment=TA_CENTER,
                    fontName=pdf_font,
                ),
            )
        )

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ── Profile update + avatar upload ───────────────────────────


from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create a UserProfile whenever a new User is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@method_decorator(csrf_exempt, name="dispatch")
class UpdateProfileView(View):
    """
    GET  /api/auth/profile/          — get current user profile
    POST /api/auth/profile/          — update full_name / bio
    POST /api/auth/profile/avatar/   — upload profile picture (multipart)
    """

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=401)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return JsonResponse(
            {"profile": profile.to_dict(), "user": _build_user_dict(request.user)}
        )

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=401)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        # Handle avatar upload — store as base64 in DB (no file system)
        if request.FILES.get("avatar"):
            import base64 as _b64

            f = request.FILES["avatar"]
            mime_type = f.content_type or "image/jpeg"
            raw_bytes = f.read()
            # Resize to max 256x256 to keep DB size reasonable
            try:
                from PIL import Image
                import io as _io

                img = Image.open(_io.BytesIO(raw_bytes))
                img.thumbnail((256, 256), Image.LANCZOS)
                buf = _io.BytesIO()
                fmt = "JPEG" if "jpeg" in mime_type or "jpg" in mime_type else "PNG"
                img.save(buf, format=fmt, quality=85)
                raw_bytes = buf.getvalue()
                mime_type = "image/jpeg" if fmt == "JPEG" else "image/png"
            except Exception:
                pass  # If Pillow not available, store full image
            b64_str = _b64.b64encode(raw_bytes).decode("utf-8")
            profile.avatar_b64 = f"data:{mime_type};base64,{b64_str}"
            profile.save()
            return JsonResponse(
                {"avatar_url": profile.avatar_url(), "message": "Avatar updated"}
            )

        # Handle JSON profile update
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        if "full_name" in data:
            profile.full_name = data["full_name"].strip()
            # Also update Django User first/last name
            parts = profile.full_name.split(" ", 1)
            request.user.first_name = parts[0]
            request.user.last_name = parts[1] if len(parts) > 1 else ""
            request.user.save(update_fields=["first_name", "last_name"])
        if "bio" in data:
            profile.bio = data["bio"]

        profile.save()
        return JsonResponse(
            {"profile": profile.to_dict(), "user": _build_user_dict(request.user)}
        )


# ── Excel Export View ──────────────────────────────────────────────────────────


@login_required
def export_excel(request):
    """Generate and download the full Balance tracker Excel workbook."""
    from .excel_export import generate_excel
    from datetime import date

    buf = generate_excel()
    filename = f"Balance_Tracker_{date.today().strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ════════════════════════════════════════════════════════════════════════════
# REMINDER ENGINE VIEWS
# ════════════════════════════════════════════════════════════════════════════

from .models import (
    ReminderRule,
    CertificateStatus,
    ReminderLog,
    REMINDER_TYPE_CHOICES,
    SALARY_TRIGGER_CHOICES,
)


@method_decorator(csrf_exempt, name="dispatch")
class ReminderRuleListView(View):
    def get(self, request):
        rules = ReminderRule.objects.all()
        return JsonResponse(
            {
                "rules": [r.to_dict() for r in rules],
                "rule_types": [
                    {"value": v, "label": l} for v, l in REMINDER_TYPE_CHOICES
                ],
                "salary_triggers": [
                    {"value": v, "label": l} for v, l in SALARY_TRIGGER_CHOICES
                ],
            }
        )

    def post(self, request):
        data = json.loads(request.body)
        rule = ReminderRule.objects.create(
            name=data["name"],
            rule_type=data.get("rule_type", "cert_maturity"),
            is_active=data.get("is_active", True),
            days_before=int(data.get("days_before", 30)),
            salary_trigger=data.get("salary_trigger", "day_of_month"),
            salary_day=int(data.get("salary_day", 25)),
            salary_message=data.get("salary_message", ""),
        )
        return JsonResponse({"rule": rule.to_dict()}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class ReminderRuleDetailView(View):
    def put(self, request, pk):
        rule = get_object_or_404(ReminderRule, pk=pk)
        data = json.loads(request.body)
        rule.name = data.get("name", rule.name)
        rule.rule_type = data.get("rule_type", rule.rule_type)
        rule.is_active = data.get("is_active", rule.is_active)
        rule.days_before = int(data.get("days_before", rule.days_before))
        rule.salary_trigger = data.get("salary_trigger", rule.salary_trigger)
        rule.salary_day = int(data.get("salary_day", rule.salary_day))
        rule.salary_message = data.get("salary_message", rule.salary_message)
        rule.save()
        return JsonResponse({"rule": rule.to_dict()})

    def delete(self, request, pk):
        rule = get_object_or_404(ReminderRule, pk=pk)
        rule.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class ReminderCheckView(View):
    """Called on page load — evaluates all active rules and returns due reminders."""

    def get(self, request):
        from datetime import date, timedelta
        import calendar as cal

        today = date.today()
        results = []
        rules = ReminderRule.objects.filter(is_active=True)

        for rule in rules:

            # ── Certificate Maturity ────────────────────────────
            if rule.rule_type == "cert_maturity":
                target = today + timedelta(days=rule.days_before)
                certs = BankCertificate.objects.filter(expiry_date=target)
                # Also check any cert expiring in ≤ days_before that hasn't fired today
                certs_range = BankCertificate.objects.filter(
                    expiry_date__gte=today,
                    expiry_date__lte=target,
                )
                for cert in certs_range:
                    days_left = (cert.expiry_date - today).days
                    # Only fire if within days_before window and not already logged today
                    already = ReminderLog.objects.filter(
                        rule=rule,
                        related_model="BankCertificate",
                        related_id=cert.id,
                        fired_on=today,
                    ).exists()
                    if not already:
                        bank_name = cert.bank.name if cert.bank else "Unknown"
                        msg = (
                            f"Certificate at {bank_name} of "
                            f"{float(cert.amount):,.2f} expires in {days_left} day(s) "
                            f"on {cert.expiry_date}."
                        )
                        ReminderLog.objects.get_or_create(
                            rule=rule,
                            related_model="BankCertificate",
                            related_id=cert.id,
                            fired_on=today,
                            defaults={"message": msg},
                        )
                        results.append(
                            {
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "rule_type": rule.rule_type,
                                "message": msg,
                                "related_id": cert.id,
                                "link": "bank-certificates",
                                "days_left": days_left,
                            }
                        )

            # ── Salary Unpaid ───────────────────────────────────
            elif rule.rule_type == "salary_unpaid":
                trigger_day = _salary_trigger_day(rule, today)
                if today.day >= trigger_day:
                    # Check if current month has any unpaid salary entry
                    unpaid = SalaryEntry.objects.filter(
                        year=today.year,
                        paid=0,
                    ).exists()
                    if unpaid:
                        already = ReminderLog.objects.filter(
                            rule=rule,
                            related_model="SalaryEntry",
                            related_id=0,
                            fired_on=today,
                        ).exists()
                        if not already:
                            msg = (
                                rule.salary_message
                                or "This month has unpaid salary entries."
                            )
                            ReminderLog.objects.get_or_create(
                                rule=rule,
                                related_model="SalaryEntry",
                                related_id=0,
                                fired_on=today,
                                defaults={"message": msg},
                            )
                            results.append(
                                {
                                    "rule_id": rule.id,
                                    "rule_name": rule.name,
                                    "rule_type": rule.rule_type,
                                    "message": msg,
                                    "link": "salary",
                                }
                            )

            # ── Salary Day ──────────────────────────────────────
            elif rule.rule_type == "salary_day":
                trigger_day = _salary_trigger_day(rule, today)
                if today.day == trigger_day:
                    already = ReminderLog.objects.filter(
                        rule=rule,
                        related_model="SalaryDay",
                        related_id=today.month,
                        fired_on=today,
                    ).exists()
                    if not already:
                        msg = (
                            rule.salary_message
                            or f'Salary day reminder for {today.strftime("%B %Y")}.'
                        )
                        ReminderLog.objects.get_or_create(
                            rule=rule,
                            related_model="SalaryDay",
                            related_id=today.month,
                            fired_on=today,
                            defaults={"message": msg},
                        )
                        results.append(
                            {
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "rule_type": rule.rule_type,
                                "message": msg,
                                "link": "salary",
                            }
                        )

            # ── Custom (future-ready, no hardcoded logic) ───────
            elif rule.rule_type == "custom":
                # Custom rules fire based on salary_day as a day-of-month trigger
                trigger_day = _salary_trigger_day(rule, today)
                if today.day == trigger_day:
                    already = ReminderLog.objects.filter(
                        rule=rule,
                        related_model="Custom",
                        related_id=today.month,
                        fired_on=today,
                    ).exists()
                    if not already:
                        msg = rule.salary_message or rule.name
                        ReminderLog.objects.get_or_create(
                            rule=rule,
                            related_model="Custom",
                            related_id=today.month,
                            fired_on=today,
                            defaults={"message": msg},
                        )
                        results.append(
                            {
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "rule_type": rule.rule_type,
                                "message": msg,
                                "link": "",
                            }
                        )

        return JsonResponse({"reminders": results, "count": len(results)})


def _salary_trigger_day(rule, today):
    """Compute the calendar day this rule fires on for the given month."""
    import calendar as cal

    last_day = cal.monthrange(today.year, today.month)[1]
    if rule.salary_trigger == "day_of_month":
        return min(rule.salary_day, last_day)
    elif rule.salary_trigger == "days_before_eom":
        return max(1, last_day - rule.salary_day)
    elif rule.salary_trigger == "days_after_som":
        return min(rule.salary_day + 1, last_day)
    return rule.salary_day


@method_decorator(csrf_exempt, name="dispatch")
class ReminderLogListView(View):
    """Return recent reminder log entries."""

    def get(self, request):
        limit = int(request.GET.get("limit", 30))
        logs = ReminderLog.objects.select_related("rule").all()[:limit]
        return JsonResponse({"logs": [l.to_dict() for l in logs]})

    def delete(self, request):
        """Clear all log entries (reset fired state)."""
        ReminderLog.objects.all().delete()
        return JsonResponse({"cleared": True})


# ════════════════════════════════════════════════════════════════════════════
# CERTIFICATE STATUS VIEWS
# ════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class CertificateStatusListView(View):
    def get(self, request):
        statuses = CertificateStatus.objects.all()
        return JsonResponse({"statuses": [s.to_dict() for s in statuses]})

    def post(self, request):
        data = json.loads(request.body)
        # If new status is default, unset any existing default
        if data.get("is_default"):
            CertificateStatus.objects.filter(is_default=True).update(is_default=False)
        s = CertificateStatus.objects.create(
            name=data["name"],
            color_hex=data.get("color_hex", "#1a6ef5"),
            is_default=data.get("is_default", False),
            is_terminal=data.get("is_terminal", False),
            order=int(data.get("order", 0)),
        )
        return JsonResponse({"status": s.to_dict()}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class CertificateStatusDetailView(View):
    def put(self, request, pk):
        s = get_object_or_404(CertificateStatus, pk=pk)
        data = json.loads(request.body)
        if data.get("is_default") and not s.is_default:
            CertificateStatus.objects.filter(is_default=True).update(is_default=False)
        s.name = data.get("name", s.name)
        s.color_hex = data.get("color_hex", s.color_hex)
        s.is_default = data.get("is_default", s.is_default)
        s.is_terminal = data.get("is_terminal", s.is_terminal)
        s.order = int(data.get("order", s.order))
        s.save()
        return JsonResponse({"status": s.to_dict()})

    def delete(self, request, pk):
        s = get_object_or_404(CertificateStatus, pk=pk)
        s.delete()
        return JsonResponse({"deleted": pk})


# ════════════════════════════════════════════════════════════════════════════
# ADVANCED REPORTS VIEWS
# ════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class SalaryReportView(View):
    """Salary + bonus analytics by year and company."""

    def get(self, request):
        from django.db.models import Sum, Count, Q

        year = request.GET.get("year")
        company_id = request.GET.get("company_id")

        qs = SalaryEntry.objects.all()
        if year:
            qs = qs.filter(year=int(year))
        if company_id:
            qs = qs.filter(company_id=int(company_id))

        # By year
        by_year = list(
            qs.values("year")
            .annotate(
                total_paid=Sum("paid"),
                total_bonus=Sum("bonus"),
                total_expected=Sum("expected"),
                paid_months=Count("id", filter=Q(paid__gt=0)),
            )
            .order_by("year")
        )

        # By company
        by_company = []
        for c in Company.objects.all().order_by("order"):
            cqs = qs.filter(company=c)
            agg = cqs.aggregate(
                total_paid=Sum("paid"),
                total_bonus=Sum("bonus"),
                total_expected=Sum("expected"),
                paid_months=Count("id", filter=Q(paid__gt=0)),
            )
            if agg["paid_months"]:
                by_company.append(
                    {
                        "company_id": c.id,
                        "company_name": c.display_name or c.name,
                        "color_hex": c.color_hex,
                        "total_paid": float(agg["total_paid"] or 0),
                        "total_bonus": float(agg["total_bonus"] or 0),
                        "total_expected": float(agg["total_expected"] or 0),
                        "paid_months": agg["paid_months"] or 0,
                    }
                )

        # Grand totals
        grand = qs.aggregate(
            total_paid=Sum("paid"),
            total_bonus=Sum("bonus"),
            total_expected=Sum("expected"),
            paid_months=Count("id", filter=Q(paid__gt=0)),
        )

        # Available years
        years = list(
            SalaryEntry.objects.values_list("year", flat=True)
            .distinct()
            .order_by("year")
        )
        companies = [
            {"id": c.id, "name": c.display_name or c.name}
            for c in Company.objects.all().order_by("order")
        ]

        return JsonResponse(
            {
                "by_year": by_year,
                "by_company": by_company,
                "grand": {
                    "total_paid": float(grand["total_paid"] or 0),
                    "total_bonus": float(grand["total_bonus"] or 0),
                    "total_expected": float(grand["total_expected"] or 0),
                    "paid_months": grand["paid_months"] or 0,
                },
                "years": years,
                "companies": companies,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class BalanceReportView(View):
    """Balance summary across banks and currencies."""

    def get(self, request):
        from django.db.models import Sum

        entries = BalanceEntry.objects.select_related("bank", "currency").all()
        banks = Bank.objects.all()

        # Group by bank
        by_bank = []
        for bank in banks:
            bank_entries = entries.filter(bank=bank)
            total_egp = float(
                bank_entries.filter(currency__code="EGP").aggregate(s=Sum("amount"))[
                    "s"
                ]
                or 0
            )
            by_bank.append(
                {
                    "bank_id": bank.id,
                    "bank_name": bank.name,
                    "total_egp": total_egp,
                    "entries": [e.to_dict() for e in bank_entries],
                }
            )

        # Unbanked entries (cash / home)
        home = entries.filter(bank__isnull=True)
        by_currency = []
        for e in home:
            by_currency.append(e.to_dict())

        # Certificate totals
        from django.db.models import Sum as S

        cert_total = float(BankCertificate.objects.aggregate(s=S("amount"))["s"] or 0)
        cert_interest = float(
            BankCertificate.objects.aggregate(s=S("interest_value"))["s"] or 0
        )

        return JsonResponse(
            {
                "by_bank": by_bank,
                "home_entries": by_currency,
                "cert_total": cert_total,
                "cert_interest": cert_interest,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class CertificateReportView(View):
    """Certificate maturity and analytics report."""

    def get(self, request):
        from datetime import date, timedelta
        from django.db.models import Sum, Count

        today = date.today()
        certs = BankCertificate.objects.select_related("bank", "currency").all()

        agg = certs.aggregate(
            total_count=Count("id"),
            total_amount=Sum("amount"),
            total_interest=Sum("interest_value"),
        )

        # Maturity buckets (configurable label from settings, days from AppSettings)
        bucket_days = [
            ("overdue", 0, -1),
            ("30_days", 0, 30),
            ("90_days", 31, 90),
            ("180_days", 91, 180),
            ("later", 181, 9999),
        ]

        buckets = {}
        for label, low, high in bucket_days:
            if label == "overdue":
                buckets[label] = [
                    c.to_dict() for c in certs.filter(expiry_date__lt=today)
                ]
            else:
                buckets[label] = [
                    c.to_dict()
                    for c in certs.filter(
                        expiry_date__gte=today + timedelta(days=low),
                        expiry_date__lte=today + timedelta(days=high),
                    )
                ]

        # By status
        by_status = {}
        for c in certs:
            by_status[c.status] = by_status.get(c.status, {"count": 0, "total": 0})
            by_status[c.status]["count"] += 1
            by_status[c.status]["total"] += float(c.amount)

        # Monthly interest cashflow (next 12 months)
        monthly_cf = []
        for i in range(12):
            m_start = today.replace(day=1) + timedelta(days=32 * i)
            m_start = m_start.replace(day=1)
            m_certs = certs.filter(
                expiry_date__year=m_start.year,
                expiry_date__month=m_start.month,
            )
            monthly_cf.append(
                {
                    "month": m_start.strftime("%b %Y"),
                    "count": m_certs.count(),
                    "amount": float(m_certs.aggregate(s=Sum("amount"))["s"] or 0),
                }
            )

        return JsonResponse(
            {
                "summary": {
                    "total_count": agg["total_count"] or 0,
                    "total_amount": float(agg["total_amount"] or 0),
                    "total_interest": float(agg["total_interest"] or 0),
                    "monthly_interest": float(agg["total_interest"] or 0),
                },
                "buckets": buckets,
                "by_status": by_status,
                "monthly_cf": monthly_cf,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class DashboardSummaryView(View):
    """Enhanced dashboard summary — salary KPIs + cert maturity + balance."""

    def get(self, request):
        from datetime import date, timedelta
        from django.db.models import Sum, Count, Q

        today = date.today()

        # Salary grand totals
        sal_agg = SalaryEntry.objects.aggregate(
            total_paid=Sum("paid"),
            total_bonus=Sum("bonus"),
            total_expected=Sum("expected"),
            paid_months=Count("id", filter=Q(paid__gt=0)),
        )

        # Certificates
        certs = BankCertificate.objects.select_related("bank").all()
        cert_agg = certs.aggregate(
            total=Sum("amount"),
            total_interest=Sum("interest_value"),
        )
        expiring_soon_days = int(AppSettings.get("cert_expiry_warning_days", "30"))
        expiring_soon = list(
            certs.filter(
                expiry_date__gte=today,
                expiry_date__lte=today + timedelta(days=expiring_soon_days),
            )
            .order_by("expiry_date")
            .values("id", "expiry_date", "amount", "status", "bank__name")
        )
        for e in expiring_soon:
            e["days_left"] = (e["expiry_date"] - today).days
            e["expiry_date"] = e["expiry_date"].isoformat()

        # Active reminders (due today)
        active_reminders = []
        for rule in ReminderRule.objects.filter(
            is_active=True, rule_type="cert_maturity"
        ):
            logs = ReminderLog.objects.filter(rule=rule, fired_on=today).values(
                "message", "related_id", "related_model"
            )
            for l in logs:
                active_reminders.append({"rule": rule.name, "message": l["message"]})

        # Balance
        bal_entries = BalanceEntry.objects.select_related("currency").all()
        egp_balance = float(
            bal_entries.filter(currency__code="EGP").aggregate(s=Sum("amount"))["s"]
            or 0
        )

        return JsonResponse(
            {
                "salary": {
                    "total_paid": float(sal_agg["total_paid"] or 0),
                    "total_bonus": float(sal_agg["total_bonus"] or 0),
                    "total_expected": float(sal_agg["total_expected"] or 0),
                    "paid_months": sal_agg["paid_months"] or 0,
                },
                "certificates": {
                    "total_amount": float(cert_agg["total"] or 0),
                    "total_interest": float(cert_agg["total_interest"] or 0),
                    "monthly_interest": float(cert_agg["total_interest"] or 0) / 12,
                    "count": certs.count(),
                },
                "expiring_soon": expiring_soon,
                "active_reminders": active_reminders,
                "egp_balance": egp_balance,
                "expiry_warning_days": expiring_soon_days,
            }
        )


from datetime import date, timedelta


@method_decorator(csrf_exempt, name="dispatch")
class CertificateForecastView(View):

    def get(self, request):

        certs = BankCertificate.objects.filter(status="Active")

        today = date.today()
        
        cash_balance = 0
        certificate_balance = 0
        forecast_30 = 0
        forecast_90 = 0
        forecast_180 = 0

        upcoming = []

        for c in certs:

            if not c.expiry_date:
                continue

            maturity_value = float(c.amount) #+ float(c.interest_value)
            days_left = (c.expiry_date - today).days

            if days_left < 0:
                continue

            if days_left <= 30:
                forecast_30 += maturity_value

            if days_left <= 90:
                forecast_90 += maturity_value

            if days_left <= 180:
                forecast_180 += maturity_value


            upcoming.append(
                {
                    "id": c.id,
                    "bank": c.bank.name if c.bank else "",
                    "expiry_date": c.expiry_date.isoformat(),
                    "amount": float(c.amount),
                    "interest": float(c.interest_value),
                    "maturity_value": maturity_value,
                    "days_left": days_left,
                }
            )
        from core.models import BalanceEntry

        egp_balances = BalanceEntry.objects.filter(
            currency__code="EGP"
        )

        for b in egp_balances:

            if b.balance_type == "certificate":
                certificate_balance += float(b.amount)
            else:
                cash_balance += float(b.amount)

        upcoming.sort(key=lambda x: x["days_left"])

                # Portfolio composition

        total_certificates = sum(
            float(c.amount)
            for c in certs
        )

        # Current balances

        from core.models import BalanceEntry as Balance

        balances = Balance.objects.all()

        cash_egp = 0
        foreign_currency = 0

        for b in balances:

            currency = (
                b.currency.code.upper()
                if b.currency
                else "EGP"
            )

            amount = float(b.amount)

            if currency == "EGP":
                cash_egp += amount
            else:
                foreign_currency += amount

        total_portfolio = (
            cash_egp +
            foreign_currency +
            total_certificates
        )

        cash_pct = (
            cash_egp / total_portfolio * 100
            if total_portfolio else 0
        )

        cert_pct = (
            total_certificates / total_portfolio * 100
            if total_portfolio else 0
        )


        recommendations = []

        if cash_pct > 40:
            recommendations.append(
                "Large amount of cash is idle. Consider investing part of it in certificates or gold."
            )

        if cert_pct > 70:
            recommendations.append(
                "Portfolio is heavily concentrated in certificates. Consider diversification."
            )

        if forecast_30 > 0:
            recommendations.append(
                f"{forecast_30:,.0f} EGP will become available within 30 days."
            )

        cash_ratio = (
            (forecast_30 / forecast_180) * 100
            if forecast_180 > 0
            else 0
        )

        if forecast_30 > 500000:
            recommendations.append(
                f"Certificates worth {forecast_30:,.0f} EGP will mature within 30 days. Review reinvestment opportunities."
            )

        if forecast_90 > forecast_30 * 2:
            recommendations.append(
                "Large certificate maturities are expected within the next 90 days. Consider staggering future investments."
            )

        if forecast_180 > 0 and cash_ratio < 25:
            recommendations.append(
                "Most certificate value is locked for longer periods. Maintain sufficient liquid cash reserves."
            )

        if not recommendations:
            recommendations.append(
                "Portfolio structure appears balanced. No immediate action is required."
            )

        future_cash_30 = cash_balance + forecast_30
        future_cash_90 = cash_balance + forecast_90
        future_cash_180 = cash_balance + forecast_180

        gold_value = 0
        grand_total = (
            cash_balance
            + certificate_balance
        )

        total_assets = grand_total if grand_total > 0 else 1

        cash_ratio = (
            cash_balance / total_assets
        ) * 100

        certificate_ratio = (
            certificate_balance / total_assets
        ) * 100

        gold_ratio = 0
        recommendations = []

        if cash_ratio > 60:
            recommendations.append(
                "Large cash position detected. Consider investing part of the cash."
            )

        if gold_ratio < 10:
            recommendations.append(
                "Gold allocation is low. Consider increasing gold exposure."
            )

        if certificate_ratio < 20:
            recommendations.append(
                "Certificate allocation is low. Consider a new certificate investment."
            )

        if forecast_30 > 0:
            recommendations.append(
                f"{forecast_30:,.0f} EGP will mature within 30 days."
            )

        if not recommendations:
            recommendations.append(
                "Current asset allocation looks balanced."
            )

        action_plan = ""

        if forecast_30 > 0:

            if cash_ratio > 60:
                action_plan = (
                    "Keep the upcoming maturity amount as cash."
                )

            elif gold_ratio < 10:
                action_plan = (
                    "Consider allocating part of the upcoming maturity amount to gold."
                )

            elif certificate_ratio < 40:
                action_plan = (
                    "Consider reinvesting the maturity amount into a new certificate."
                )

            else:
                action_plan = (
                    "Split the maturity amount between cash and gold."
                )

        return JsonResponse(
            {
                "cash_balance": cash_balance,
                "certificate_balance": certificate_balance,

                "future_cash_30": future_cash_30,
                "future_cash_90": future_cash_90,
                "future_cash_180": future_cash_180,

                "forecast_30": forecast_30,
                "forecast_90": forecast_90,
                "forecast_180": forecast_180,


                "upcoming": upcoming[:10],
                "cash_ratio": round(cash_ratio, 1),
                "certificate_ratio": round(certificate_ratio, 1),
                "gold_ratio": round(gold_ratio, 1),

                "recommendations": recommendations,
                "action_plan": action_plan,
            }
        )