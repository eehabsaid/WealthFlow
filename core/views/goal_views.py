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
class GoalPlanningView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        _run_certificate_interest_sync()
        payload = GoalPlanningService(today=datetime.date.today()).payload()
        return JsonResponse(payload)




@method_decorator(csrf_exempt, name="dispatch")
class GoalListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        goals = Goal.objects.select_related("currency", "linked_asset").all().order_by("target_date", "id")
        return JsonResponse({"goals": [goal.to_dict() for goal in goals]})

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        data = json.loads(request.body or "{}")
        goal = Goal.objects.create(
            name=data.get("name", "").strip(),
            goal_type=data.get("goal_type", "").strip(),
            target_amount=data.get("target_amount", 0) or 0,
            currency_id=data.get("currency_id") or None,
            target_date=_parse_iso_date(data.get("target_date")),
            current_saved_amount=data.get("current_saved_amount", 0) or 0,
            linked_asset_id=data.get("linked_asset_id") or None,
            priority=data.get("priority", "Medium"),
            notes=data.get("notes", ""),
        )
        return JsonResponse(goal.to_dict(), status=201)




@method_decorator(csrf_exempt, name="dispatch")
class GoalDetailView(View):
    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        goal = get_object_or_404(Goal, pk=pk)
        data = json.loads(request.body or "{}")

        for field in ["name", "goal_type", "target_amount", "current_saved_amount", "priority", "notes"]:
            if field in data:
                setattr(goal, field, data[field])

        if "currency_id" in data:
            goal.currency_id = data.get("currency_id") or None
        if "linked_asset_id" in data:
            goal.linked_asset_id = data.get("linked_asset_id") or None
        if "target_date" in data:
            goal.target_date = _parse_iso_date(data.get("target_date"))

        goal.save()
        return JsonResponse(goal.to_dict())

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        goal = get_object_or_404(Goal, pk=pk)
        goal.delete()
        return JsonResponse({"deleted": pk})

# ============================================================
# Fixed Assets APIs
# ============================================================






