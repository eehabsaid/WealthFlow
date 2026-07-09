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



def _parse_iso_date(value):
    if not value:
        return None
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return value
    return value




@login_required(login_url="/accounts/login/")
def index(request):
    return render(request, "index.html")




def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None




@method_decorator(csrf_exempt, name="dispatch")
class DashboardSummaryView(View):
    """Enhanced dashboard summary — salary KPIs + cert maturity + balance."""

    def get(self, request):
        _run_certificate_interest_sync()
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

        net_worth = NetWorthService().portfolio_components()

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
                    "monthly_interest": float(cert_agg["total_interest"] or 0),
                    "count": certs.count(),
                },
                "expiring_soon": expiring_soon,
                "active_reminders": active_reminders,
                "egp_balance": egp_balance,
                "expiry_warning_days": expiring_soon_days,
                "net_worth": {
                    "total": float(net_worth["net_worth_egp"]),
                    "liquid_assets": float(net_worth["liquid_assets_total_egp"]),
                    "fixed_assets": float(net_worth["fixed_assets_total_egp"]),
                },
            }
        )


from datetime import date, timedelta
from core.models import SalaryEntry




@method_decorator(csrf_exempt, name="dispatch")
class CertificateForecastView(View):
    def get(self, request):
        _run_certificate_interest_sync()
        return JsonResponse(NetWorthService().certificate_forecast_payload(today=datetime.date.today()))




@method_decorator(csrf_exempt, name="dispatch")
class CashFlowForecastView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        _run_certificate_interest_sync()
        payload = CashFlowForecastService(today=datetime.date.today()).payload()
        return JsonResponse(payload)




@method_decorator(csrf_exempt, name="dispatch")
class WealthGrowthForecastView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        _run_certificate_interest_sync()
        payload = WealthGrowthForecastService(today=datetime.date.today()).payload()
        return JsonResponse(payload)




@method_decorator(csrf_exempt, name="dispatch")
class PortfolioOptimizerView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        _run_certificate_interest_sync()
        payload = PortfolioOptimizerService(today=datetime.date.today()).payload()
        return JsonResponse(payload)


