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


def _clear_non_selected_asset_details(asset):
    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES and hasattr(asset, "real_estate"):
        asset.real_estate.delete()

    if asset.asset_type not in VEHICLE_ASSET_TYPES and hasattr(asset, "vehicle_details"):
        asset.vehicle_details.delete()

    if asset.asset_type not in GOLD_ASSET_TYPES and hasattr(asset, "gold_details"):
        asset.gold_details.delete()

    if asset.asset_type not in OTHER_ASSET_TYPES and hasattr(asset, "other_asset_details"):
        asset.other_asset_details.delete()


@method_decorator(csrf_exempt, name="dispatch")
class FixedAssetListView(View):

    def get(self, request):
        qs = FixedAsset.objects.all().order_by("name")

        asset_type = request.GET.get("asset_type")
        status = request.GET.get("status")

        if asset_type:
            qs = qs.filter(asset_type=asset_type)

        if status:
            qs = qs.filter(status=status)

        service = NetWorthService()
        return JsonResponse(
            {
                "assets": [a.to_dict() for a in qs],
                "portfolio_snapshot": service.fixed_assets_snapshot(),
            }
        )

    def post(self, request):
        data = json.loads(request.body)
        re = data.get("real_estate_details")
        vehicle_details = data.get("vehicle_details")
        gold_details = data.get("gold_details")
        other_asset_details = data.get("other_asset_details")

        purchase_rows_raw = data.get("purchase_payments", [])

        try:
            with transaction.atomic():
                purchase_rows = _normalize_purchase_payments_payload(
                    purchase_rows_raw,
                    data.get("purchase_price", 0),
                    purchase_currency_id=data.get("purchase_currency_id"),
                )

                asset = FixedAsset.objects.create(
                    name=data["name"],
                    asset_type=data["asset_type"],
                    status=data.get("status", "Owned"),
                    purchase_date=data["purchase_date"],
                    purchase_price=data.get("purchase_price", 0),
                    purchase_usd_rate=data.get("purchase_usd_rate", 0),
                    purchase_price_usd=data.get("purchase_price_usd", 0),
                    current_market_value=data.get("current_market_value", 0),
                    valuation_source=data.get("valuation_source", "Manual"),
                    last_valuation_date=data.get("last_valuation_date") or None,
                    notes=data.get("notes", ""),
                )

                if re:
                    RealEstateDetails.objects.create(
                        asset=asset,
                        country=re.get("country", "Egypt"),
                        governorate=re.get("governorate", ""),
                        city=re.get("city", ""),
                        district=re.get("district", ""),
                        full_address=re.get("address", ""),
                        area_m2=re.get("apartment_area", 0),
                        bedrooms=re.get("rooms", 0),
                        bathrooms=re.get("bathrooms", 0),
                        floor_number=re.get("floor", 0),
                        building_floors=re.get("building_floors", 0),
                        build_year=re.get("building_year") or None,
                        facing=re.get("facades", ""),
                        finishing_level=re.get("finishing_level", ""),
                        electricity_meter_private=re.get("electricity", False),
                        water_meter_private=re.get("water", False),
                        has_gas=re.get("gas", False),
                        has_elevator=re.get("elevator", False),
                        has_garage=re.get("garage", False),
                        has_land_share=re.get("has_land_share", False),
                        land_share_ratio=re.get("land_share", ""),
                        land_share_sqm=float(re.get("land_share_sqm") or 0),
                        latitude=re.get("latitude") or None,
                        longitude=re.get("longitude") or None,
                        licensed=re.get("licensed", False),
                        description=re.get("description", ""),
                    )

                _sync_vehicle_details(asset, vehicle_details)
                _sync_gold_details(asset, gold_details)
                _sync_other_asset_details(asset, other_asset_details)

                _sync_asset_mortgage(asset, data.get("mortgage_details"))
                _sync_asset_rental(asset, data.get("rental_details"))

                for item in data.get("renovations", []):
                    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES:
                        break

                    AssetRenovation.objects.create(
                        asset=asset,
                        date=item.get("date") or None,
                        category=item.get("category", ""),
                        description=item.get("description", ""),
                        amount_egp=item.get("amount_egp", 0),
                        usd_rate=item.get("usd_rate", 0),
                        amount_usd=item.get("amount_usd", 0),
                        notes=item.get("notes", ""),
                    )

                _sync_asset_maintenance(asset, data.get("maintenance", []))
                _sync_asset_insurance(asset, data.get("insurance", []))
                _sync_asset_furniture(asset, data.get("furniture", []))
                _sync_asset_valuation_history(asset, data.get("valuation_history", []))
                _clear_non_selected_asset_details(asset)

                _apply_asset_purchase_rows_delta(purchase_rows, sign=-1)
                _sync_asset_purchase_payments(asset, purchase_rows)

                _sync_gold_balance_from_assets()

        except ValueError as exc:
            return JsonResponse(
                {
                    "error": str(exc),
                    "error_key": str(exc),
                },
                status=400,
            )

        return JsonResponse(asset.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class FixedAssetDetailView(View):

    def get(self, request, pk):
        asset = get_object_or_404(FixedAsset, pk=pk)
        return JsonResponse(asset.to_dict())

    def put(self, request, pk):
        asset = get_object_or_404(FixedAsset, pk=pk)

        data = json.loads(request.body)
        vehicle_details = data.get("vehicle_details")
        gold_details = data.get("gold_details")
        other_asset_details = data.get("other_asset_details")

        fields = [
            "name",
            "asset_type",
            "status",
            "purchase_date",
            "purchase_price",
            "purchase_usd_rate",
            "purchase_price_usd",
            "current_market_value",
            "valuation_source",
            "last_valuation_date",
            "notes",
        ]

        previous_rows = _purchase_rows_from_instances(
            AssetPurchasePayment.objects.filter(asset=asset).order_by("id")
        )

        purchase_rows_payload_present = "purchase_payments" in data
        purchase_rows_raw = data.get("purchase_payments", [])

        try:
            with transaction.atomic():
                if purchase_rows_payload_present:
                    allow_empty = len(previous_rows) == 0
                    purchase_rows = _normalize_purchase_payments_payload(
                        purchase_rows_raw,
                        data.get("purchase_price", asset.purchase_price),
                        purchase_currency_id=data.get("purchase_currency_id"),
                        allow_empty=allow_empty,
                    )
                else:
                    purchase_rows = previous_rows

                if previous_rows:
                    _apply_asset_purchase_rows_delta(previous_rows, sign=1)

                for field in fields:
                    if field in data:
                        setattr(asset, field, data[field])

                asset.save()

                re = data.get("real_estate_details")

                if re:
                    obj, _ = RealEstateDetails.objects.get_or_create(asset=asset)

                    obj.country = re.get("country", "Egypt")
                    obj.governorate = re.get("governorate", "")
                    obj.city = re.get("city", "")
                    obj.district = re.get("district", "")
                    obj.full_address = re.get("address", "")

                    obj.area_m2 = re.get("apartment_area", 0)

                    obj.bedrooms = re.get("rooms", 0)
                    obj.bathrooms = re.get("bathrooms", 0)

                    obj.floor_number = re.get("floor", 0)
                    obj.building_floors = re.get("building_floors", 0)
                    obj.build_year = re.get("building_year") or None

                    obj.facing = re.get("facades", "")

                    obj.furnished_status = re.get("furnished_status", "Unfurnished")
                    obj.finishing_level = re.get("finishing_level", "")

                    obj.electricity_meter_private = re.get("electricity", False)
                    obj.water_meter_private = re.get("water", False)
                    obj.has_gas = re.get("gas", False)

                    obj.has_elevator = re.get("elevator", False)
                    obj.has_garage = re.get("garage", False)
                    obj.has_land_share = re.get("has_land_share", False)
                    obj.land_share_ratio = re.get("land_share", "")
                    obj.land_share_sqm = float(re.get("land_share_sqm") or 0)
                    obj.latitude = re.get("latitude") or None
                    obj.longitude = re.get("longitude") or None
                    obj.licensed = re.get("licensed", False)
                    obj.description = re.get("description", "")

                    obj.save()
                elif asset.asset_type not in REAL_ESTATE_ASSET_TYPES and hasattr(asset, "real_estate"):
                    asset.real_estate.delete()

                _sync_vehicle_details(asset, vehicle_details)
                _sync_gold_details(asset, gold_details)
                _sync_other_asset_details(asset, other_asset_details)

                AssetRenovation.objects.filter(asset=asset).delete()

                for item in data.get("renovations", []):
                    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES:
                        break

                    AssetRenovation.objects.create(
                        asset=asset,
                        date=item.get("date") or None,
                        category=item.get("category", ""),
                        description=item.get("description", ""),
                        amount_egp=item.get("amount_egp", 0),
                        usd_rate=item.get("usd_rate", 0),
                        amount_usd=item.get("amount_usd", 0),
                        notes=item.get("notes", ""),
                    )

                _sync_asset_maintenance(asset, data.get("maintenance", []))
                _sync_asset_insurance(asset, data.get("insurance", []))
                _sync_asset_mortgage(asset, data.get("mortgage_details"))
                _sync_asset_rental(asset, data.get("rental_details"))
                _sync_asset_furniture(asset, data.get("furniture", []))
                _sync_asset_valuation_history(asset, data.get("valuation_history", []))
                _clear_non_selected_asset_details(asset)

                if purchase_rows_payload_present:
                    if purchase_rows:
                        _apply_asset_purchase_rows_delta(purchase_rows, sign=-1)
                        _sync_asset_purchase_payments(asset, purchase_rows)
                    else:
                        AssetPurchasePayment.objects.filter(asset=asset).delete()
                elif previous_rows:
                    _apply_asset_purchase_rows_delta(previous_rows, sign=-1)

                _sync_gold_balance_from_assets()

        except ValueError as exc:
            return JsonResponse(
                {
                    "error": str(exc),
                    "error_key": str(exc),
                },
                status=400,
            )

        return JsonResponse(asset.to_dict())

    def delete(self, request, pk):
        asset = get_object_or_404(FixedAsset, pk=pk)

        purchase_rows = _purchase_rows_from_instances(
            AssetPurchasePayment.objects.filter(asset=asset).order_by("id")
        )

        try:
            with transaction.atomic():
                # Reverse only when this asset has explicit payment-source rows.
                if purchase_rows:
                    _apply_asset_purchase_rows_delta(purchase_rows, sign=1)

                asset.delete()
                _sync_gold_balance_from_assets()
        except ValueError as exc:
            return JsonResponse(
                {
                    "error": str(exc),
                    "error_key": str(exc),
                },
                status=400,
            )

        return JsonResponse({"deleted": pk})


