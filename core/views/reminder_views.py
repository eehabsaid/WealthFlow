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
        result = ReminderAutomationService().evaluate(today=timezone.localdate()).to_dict()
        return JsonResponse(result)




@method_decorator(csrf_exempt, name="dispatch")
class FixedAssetValuationRefreshView(View):
    def post(self, request, pk):
        asset = get_object_or_404(FixedAsset, pk=pk)
        updated, provider_name = PropertyValuationService().refresh_asset(asset, today=timezone.localdate())
        asset.refresh_from_db()
        return JsonResponse(
            {
                "updated": updated,
                "provider": provider_name,
                "asset": asset.to_dict(),
            }
        )




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


