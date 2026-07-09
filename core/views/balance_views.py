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
class BalanceListView(View):
    def _normalize_purity_key(self, purity_value):
        text = str(purity_value or "").strip().lower()
        if "24" in text or "999" in text:
            return "24k"
        if "22" in text or "916" in text:
            return "22k"
        if "21" in text or "875" in text:
            return "21k"
        if "18" in text or "750" in text:
            return "18k"
        return "24k"

    def _cashback_per_gram_for_purity(self, purity_value):
        key = self._normalize_purity_key(purity_value)
        setting = GoldPuritySetting.objects.filter(key=key, is_active=True).first()
        return float(setting.cashback_per_gram) if setting else 0.0

    def _sell_per_gram_for_purity(self, latest_gold, purity_value):
        if not latest_gold:
            return 0.0
        key = self._normalize_purity_key(purity_value)
        if key == "22k":
            return float(latest_gold.carat_22k or 0)
        if key == "21k":
            return float(latest_gold.carat_21k or 0)
        if key == "18k":
            return float(latest_gold.carat_18k or 0)
        return float(latest_gold.carat_24k or 0)

    def get(self, request):
        _run_certificate_interest_sync()
        return JsonResponse(NetWorthService().balance_payload())

    def post(self, request):
        data = json.loads(request.body)
        balance_type = data["balance_type"]
        purity = data.get("purity", "")
        if balance_type == BalanceEntry.BalanceType.GOLD:
            purity = _normalize_gold_purity(purity)
        else:
            purity = ""

        entry = BalanceEntry.objects.create(
            title=data["title"],
            balance_type=balance_type,
            bank_id=data.get("bank_id"),
            currency_id=data.get("currency_id", 1),
            purity=purity,
            amount=data.get("amount", 0),
            notes=data.get("notes", ""),
        )
        return JsonResponse(entry.to_dict(), status=201)




@method_decorator(csrf_exempt, name="dispatch")
class BalanceDetailView(View):
    def put(self, request, pk):
        entry = get_object_or_404(BalanceEntry, pk=pk)
        data = json.loads(request.body)
        for field in [
            "title",
            "balance_type",
            "bank_id",
            "currency_id",
            "amount",
            "notes",
            "purity",
        ]:
            if field in data:
                setattr(entry, field, data[field])

        if entry.balance_type == BalanceEntry.BalanceType.GOLD:
            entry.purity = _normalize_gold_purity(entry.purity)
        else:
            entry.purity = ""

        entry.save()
        return JsonResponse(entry.to_dict())

    def delete(self, request, pk):
        entry = get_object_or_404(BalanceEntry, pk=pk)
        entry.delete()
        return JsonResponse({"deleted": pk})


