# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from decimal import Decimal, InvalidOperation
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ValidationError
from core.models import (
    Company,
    SalaryEntry,
    Bank,
    BalanceEntry,
    AppSettings,
    ExchangeRate,
    GoldPrice,
    GoldPriceHistory,
    Currency,
    ExpenseCategory,
    ExpenseSubcategory,
    Expense,
    BankCertificate,
    BankCertificateInterestHistory,
    _is_certificate_active,
    PagePermission,
    PAGE_PERMISSION_CHOICES,
    UserProfile,
    ReminderRule,
    CertificateStatus,
    ReminderLog,
    REMINDER_TYPE_CHOICES,
    SALARY_TRIGGER_CHOICES,
    FixedAsset,
    RealEstateDetails,
    VehicleDetails,
    GoldDetails,
    OtherAssetDetails,
    AssetRenovation,
    AssetMaintenance,
    AssetInsurance,
    AssetFurniture,
    AssetValuationHistory,
    AssetPurchasePayment,
    AssetSale,
    AssetPhoto,
    AssetMortgage,
    AssetRental,
    GoldTypeSetting,
    GoldPuritySetting,
    EmailTemplate,
    Goal,
    PerDiem,

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
    Image as RLImage,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from django.views.decorators.http import require_http_methods
from core.services.balance.net_worth_service import NetWorthService
from core.services.balance.financial_sync_service import FinancialSyncService
from core.services.shared.document_service import DocumentService
from core.services.shared.exchange_rate_service import ExchangeRateService
from core.services.fixed_assets.gold_valuation_service import GoldValuationService
from core.services.fixed_assets.property_valuation_service import PropertyValuationService
from core.services.shared.reminder_automation_service import ReminderAutomationService
from core.services.shared.auth_workflow_service import AuthWorkflowService, EmailTemplateService
from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.financial_advisor.goal_planning_service import GoalPlanningService
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.wealth_growth_forecast_service import WealthGrowthForecastService



from django.contrib.auth import get_user_model
User = get_user_model()
from core.constants import (
    PAGE_PERMISSION_KEYS,
    MONTH_ORDER,
    REAL_ESTATE_ASSET_TYPES,
    VEHICLE_ASSET_TYPES,
    GOLD_ASSET_TYPES,
    OTHER_ASSET_TYPES,
    ASSET_PAYMENT_METHOD_CASH,
    ASSET_PAYMENT_METHOD_CARD,
    ASSET_PAYMENT_METHOD_BANK,
    ASSET_PAYMENT_METHOD_BANK_TRANSFER,
    ASSET_PAYMENT_METHOD_NORMALIZED,
    GOLD_UNIT_TO_GRAMS,
)
from core.utils import (
    _parse_iso_date,
    month_sort_key,
    _to_decimal,
    _gold_unit_factor,
    _gold_weight_in_grams,
    _normalize_gold_purity,
    _gold_sell_price_per_gram,
    _gold_cashback_per_gram,
)
from core.validators import _api_auth_required

from django.db.models.signals import post_save
from django.dispatch import receiver

import sys
if not __name__.endswith('.auth_views') and not __name__ == 'core.views.auth_views':
    try:
        from .auth_views import AdminRequiredMixin
    except (ImportError, ValueError):
        pass

if not __name__.endswith('.certificate_views') and not __name__ == 'core.views.certificate_views':
    try:
        from .certificate_views import _run_certificate_interest_sync
    except (ImportError, ValueError):
        pass



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


