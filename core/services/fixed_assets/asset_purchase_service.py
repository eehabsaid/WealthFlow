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


def _normalize_asset_payment_method(method_value):
    normalized = str(method_value or "").strip().lower()
    return ASSET_PAYMENT_METHOD_NORMALIZED.get(normalized, ASSET_PAYMENT_METHOD_CASH)


def _asset_payment_requires_bank(method_value):
    return _normalize_asset_payment_method(method_value) != ASSET_PAYMENT_METHOD_CASH


def _asset_payment_currency_required(currency_id):
    return currency_id is not None and str(currency_id).strip() != ""


def _default_egp_currency_id():
    currency = Currency.objects.filter(code__iexact="EGP").order_by("id").first()
    return currency.id if currency else None


def _normalize_purchase_payments_payload(rows, purchase_price, purchase_currency_id=None, allow_empty=False):
    normalized_rows = []
    running_total = Decimal("0")
    resolved_currency_id = purchase_currency_id

    if rows is None:
        rows = []

    if not isinstance(rows, list):
        raise ValueError("purchase_payments_invalid")

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("purchase_payments_invalid")

        row_currency_id = row.get("currency_id")
        if not _asset_payment_currency_required(resolved_currency_id) and _asset_payment_currency_required(row_currency_id):
            resolved_currency_id = row_currency_id

        payment_method = _normalize_asset_payment_method(row.get("payment_method"))
        bank_id = row.get("bank_id")
        if _asset_payment_requires_bank(payment_method) and not bank_id:
            raise ValueError("bank_account_required")
        if payment_method == ASSET_PAYMENT_METHOD_CASH:
            bank_id = None

        amount = _to_decimal(row.get("amount"), default="0")
        if amount <= 0:
            raise ValueError("amount_required")

        normalized_rows.append(
            {
                "currency_id": None,
                "payment_method": payment_method,
                "bank_id": int(bank_id) if bank_id else None,
                "amount": amount,
            }
        )
        running_total += amount

    if not _asset_payment_currency_required(resolved_currency_id):
        if allow_empty and not normalized_rows:
            return []
        resolved_currency_id = _default_egp_currency_id()
        if not resolved_currency_id:
            raise ValueError("currency_required")

    resolved_currency_id = int(resolved_currency_id)
    for row in normalized_rows:
        row["currency_id"] = resolved_currency_id

    if not normalized_rows:
        if allow_empty:
            return []

        return [
            {
                "currency_id": resolved_currency_id,
                "payment_method": ASSET_PAYMENT_METHOD_CASH,
                "bank_id": None,
                "amount": _to_decimal(purchase_price),
            }
        ]

    target_total = _to_decimal(purchase_price)
    if running_total.quantize(Decimal("0.01")) != target_total.quantize(Decimal("0.01")):
        raise ValueError("purchase_payment_total_mismatch")

    return normalized_rows


def _get_asset_cash_balance_entry(currency_id, bank_id):
    qs = BalanceEntry.objects.select_for_update().filter(
        balance_type=BalanceEntry.BalanceType.CASH,
        currency_id=currency_id,
    )
    if bank_id:
        qs = qs.filter(bank_id=bank_id)
    else:
        qs = qs.filter(bank__isnull=True)
    return qs.order_by("id").first()


def _apply_asset_balance_delta(currency_id, payment_method, bank_id, amount_delta):
    delta = _to_decimal(amount_delta)
    if delta == 0:
        return

    resolved_method = _normalize_asset_payment_method(payment_method)
    resolved_bank_id = bank_id if _asset_payment_requires_bank(resolved_method) else None

    entry = _get_asset_cash_balance_entry(currency_id, resolved_bank_id)
    if not entry:
        raise ValueError("matching_balance_entry_not_found")

    next_amount = _to_decimal(entry.amount) + delta
    if next_amount < 0:
        raise ValueError("insufficient_balance")

    entry.amount = next_amount
    entry.save(update_fields=["amount"])


def _apply_asset_purchase_rows_delta(rows, sign):
    sign_multiplier = Decimal("1") if sign >= 0 else Decimal("-1")
    for row in rows:
        _apply_asset_balance_delta(
            currency_id=row.get("currency_id"),
            payment_method=row.get("payment_method"),
            bank_id=row.get("bank_id"),
            amount_delta=sign_multiplier * _to_decimal(row.get("amount")),
        )


def _purchase_rows_from_instances(instances):
    return [
        {
            "currency_id": item.currency_id,
            "payment_method": item.payment_method,
            "bank_id": item.bank_id,
            "amount": _to_decimal(item.amount),
        }
        for item in instances
    ]


def _sync_asset_purchase_payments(asset, rows):
    AssetPurchasePayment.objects.filter(asset=asset).delete()
    for row in rows:
        AssetPurchasePayment.objects.create(
            asset=asset,
            currency_id=row["currency_id"],
            payment_method=row["payment_method"],
            bank_id=row.get("bank_id"),
            amount=row["amount"],
        )


