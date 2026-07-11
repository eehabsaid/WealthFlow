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


def _sync_other_asset_details(asset, details_data):
    if asset.asset_type not in OTHER_ASSET_TYPES or not details_data:
        if hasattr(asset, "other_asset_details"):
            asset.other_asset_details.delete()
        return

    OtherAssetDetails.objects.update_or_create(
        asset=asset,
        defaults={
            "category": details_data.get("category", ""),
            "manufacturer": details_data.get("manufacturer", ""),
            "model": details_data.get("model", ""),
            "serial_number": details_data.get("serial_number", ""),
            "description": details_data.get("description", ""),
            "warranty_expiry": details_data.get("warranty_expiry") or None,
            "notes": details_data.get("notes", ""),
        },
    )


def _sync_asset_mortgage(asset, mortgage_data):
    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES or not mortgage_data:
        if hasattr(asset, "mortgage"):
            asset.mortgage.delete()
        return

    has_values = any(
        mortgage_data.get(key) not in (None, "", 0, 0.0)
        for key in [
            "loan_amount",
            "remaining_balance",
            "monthly_installment",
            "interest_rate",
            "start_date",
            "end_date",
        ]
    )

    if not has_values:
        if hasattr(asset, "mortgage"):
            asset.mortgage.delete()
        return

    AssetMortgage.objects.update_or_create(
        asset=asset,
        defaults={
            "loan_amount": mortgage_data.get("loan_amount", 0),
            "remaining_balance": mortgage_data.get("remaining_balance", 0),
            "monthly_installment": mortgage_data.get("monthly_installment", 0),
            "interest_rate": mortgage_data.get("interest_rate", 0),
            "start_date": _parse_iso_date(mortgage_data.get("start_date")),
            "end_date": _parse_iso_date(mortgage_data.get("end_date")),
        },
    )


def _sync_asset_rental(asset, rental_data):
    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES or not rental_data:
        if hasattr(asset, "rental"):
            asset.rental.delete()
        return

    has_values = any(
        rental_data.get(key) not in (None, "", 0, 0.0)
        for key in [
            "monthly_rent",
            "occupancy_rate",
            "tenant_name",
            "contract_start",
            "contract_end",
            "notes",
        ]
    )

    if not has_values:
        if hasattr(asset, "rental"):
            asset.rental.delete()
        return

    AssetRental.objects.update_or_create(
        asset=asset,
        defaults={
            "monthly_rent": rental_data.get("monthly_rent", 0),
            "occupancy_rate": rental_data.get("occupancy_rate", 0),
            "tenant_name": rental_data.get("tenant_name", ""),
            "contract_start": _parse_iso_date(rental_data.get("contract_start")),
            "contract_end": _parse_iso_date(rental_data.get("contract_end")),
            "notes": rental_data.get("notes", ""),
        },
    )


