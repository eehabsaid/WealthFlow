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


@method_decorator(csrf_exempt, name="dispatch")
class AssetSaleView(View):

    def get(self, request, asset_id):
        asset = get_object_or_404(FixedAsset, pk=asset_id)

        if hasattr(asset, "sale"):
            return JsonResponse(asset.sale.to_dict())

        return JsonResponse({}, status=404)

    def post(self, request, asset_id):
        asset = get_object_or_404(FixedAsset, pk=asset_id)

        data = json.loads(request.body)
        sale_date_value = data.get("sale_date")
        if isinstance(sale_date_value, str):
            try:
                sale_date_value = datetime.date.fromisoformat(sale_date_value)
            except ValueError:
                pass

        existing_sale = getattr(asset, "sale", None)

        try:
            with transaction.atomic():
                if existing_sale is not None:
                    previous_row = _sale_payment_row(existing_sale)
                    _apply_asset_balance_delta(
                        currency_id=previous_row["currency_id"],
                        payment_method=previous_row["payment_method"],
                        bank_id=previous_row["bank_id"],
                        amount_delta=-_to_decimal(previous_row["amount"]),
                    )

                deposit_values = _resolve_sale_deposit_values(data, existing_sale=existing_sale)

                sale, created = AssetSale.objects.update_or_create(
                    asset=asset,
                    defaults={
                        "sale_date": sale_date_value,
                        "sale_price": data["sale_price"],
                        "selling_expenses": data.get("selling_expenses", 0),
                        "net_sale_amount": data["net_sale_amount"],
                        "deposit_balance_id": data.get("deposit_balance_id"),
                        "deposit_currency_id": deposit_values["deposit_currency_id"],
                        "deposit_method": deposit_values["deposit_method"],
                        "deposit_bank_id": deposit_values["deposit_bank_id"],
                        "notes": data.get("notes", ""),
                    },
                )

                current_row = _sale_payment_row(sale)
                _apply_asset_balance_delta(
                    currency_id=current_row["currency_id"],
                    payment_method=current_row["payment_method"],
                    bank_id=current_row["bank_id"],
                    amount_delta=_to_decimal(current_row["amount"]),
                )

                asset.status = "Sold"
                asset.save()
                _sync_gold_balance_from_assets()

        except ValueError as exc:
            return JsonResponse(
                {
                    "error": str(exc),
                    "error_key": str(exc),
                },
                status=400,
            )

        return JsonResponse(sale.to_dict(), status=201 if created else 200)

    def delete(self, request, asset_id):
        asset = get_object_or_404(FixedAsset, pk=asset_id)

        if not hasattr(asset, "sale"):
            return JsonResponse({}, status=404)

        try:
            with transaction.atomic():
                sale_row = _sale_payment_row(asset.sale)
                _apply_asset_balance_delta(
                    currency_id=sale_row["currency_id"],
                    payment_method=sale_row["payment_method"],
                    bank_id=sale_row["bank_id"],
                    amount_delta=-_to_decimal(sale_row["amount"]),
                )

                asset.sale.delete()

                if asset.status == "Sold":
                    asset.status = "Owned"
                    asset.save()

                _sync_gold_balance_from_assets()

        except ValueError as exc:
            return JsonResponse(
                {
                    "error": str(exc),
                    "error_key": str(exc),
                },
                status=400,
            )

        return JsonResponse({"deleted": True})


