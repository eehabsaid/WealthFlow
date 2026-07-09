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



def _to_decimal(value, default="0"):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)




def _gold_unit_factor(unit_value):
    normalized = str(unit_value or "gram").strip().lower()
    return GOLD_UNIT_TO_GRAMS.get(normalized, Decimal("1"))




def _gold_weight_in_grams(weight_value, unit_value):
    return _to_decimal(weight_value) * _gold_unit_factor(unit_value)




def _normalize_gold_purity(purity_value):
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




def _gold_sell_price_per_gram(latest_gold_price, purity_key):
    price_map = {
        "24k": _to_decimal(latest_gold_price.carat_24k),
        "22k": _to_decimal(latest_gold_price.carat_22k),
        "21k": _to_decimal(latest_gold_price.carat_21k),
        "18k": _to_decimal(latest_gold_price.carat_18k),
    }
    return price_map.get(purity_key, price_map["24k"])




def _gold_cashback_per_gram(purity_value):
    key = _normalize_gold_purity(purity_value)
    setting = GoldPuritySetting.objects.filter(key=key, is_active=True).first()
    if not setting:
        return Decimal("0")
    return _to_decimal(setting.cashback_per_gram)




def _latest_gold_price():
    return GoldPrice.objects.order_by("-fetched_at").first()




def _refresh_gold_asset_pricing(asset, gold_details=None, latest_gold_price=None):
    if asset.asset_type not in GOLD_ASSET_TYPES:
        return

    details = gold_details
    if details is None:
        details = getattr(asset, "gold_details", None)
    if details is None:
        return

    latest_gold = latest_gold_price or _latest_gold_price()
    if latest_gold is None:
        return

    usd_to_egp = _to_decimal(latest_gold.usd_to_egp)
    if usd_to_egp > 0:
        asset.purchase_usd_rate = usd_to_egp
        asset.purchase_price_usd = _to_decimal(asset.purchase_price) / usd_to_egp

    purity_key = _normalize_gold_purity(details.purity)
    sell_price_per_gram = _gold_sell_price_per_gram(latest_gold, purity_key)
    unit_factor = _gold_unit_factor(details.unit)
    details.market_price = sell_price_per_gram * unit_factor

    cashback_per_gram = _gold_cashback_per_gram(details.purity)
    details.cashback_per_gram = cashback_per_gram
    total_weight_grams = _gold_weight_in_grams(details.weight, details.unit)
    asset.current_market_value = total_weight_grams * (sell_price_per_gram + cashback_per_gram)
    asset.valuation_source = "Automatic"
    asset.last_valuation_date = timezone.now().date()

    details.save(update_fields=["market_price", "updated_at"])
    asset.save(
        update_fields=[
            "purchase_usd_rate",
            "purchase_price_usd",
            "current_market_value",
            "valuation_source",
            "last_valuation_date",
            "updated_at",
        ]
    )




def _sync_gold_balance_from_assets():
    gold_currency = Currency.objects.filter(code__iexact="gold").first()
    if not gold_currency:
        return

    gold_assets = (
        FixedAsset.objects.filter(asset_type__in=GOLD_ASSET_TYPES, status="Owned")
        .select_related("gold_details")
        .order_by("id")
    )

    grams_by_purity = {}
    for asset in gold_assets:
        details = getattr(asset, "gold_details", None)
        if details is None:
            continue
        grams = _gold_weight_in_grams(details.weight, details.unit)
        purity_key = _normalize_gold_purity(details.purity)
        grams_by_purity[purity_key] = grams_by_purity.get(purity_key, Decimal("0")) + grams

    balance_qs = BalanceEntry.objects.filter(
        balance_type=BalanceEntry.BalanceType.GOLD,
        currency_id=gold_currency.id,
    ).order_by("id")

    if not grams_by_purity:
        balance_qs.delete()
        return

    existing_by_purity = {str(e.purity or "").lower(): e for e in balance_qs}
    used_ids = []
    for purity_key, grams in grams_by_purity.items():
        entry = existing_by_purity.get(purity_key)
        title = f"{gold_currency.name or 'Gold'} {purity_key.upper()}"
        amount = grams.quantize(Decimal("0.01"))

        if entry:
            entry.title = title
            entry.bank = None
            entry.amount = amount
            entry.notes = ""
            entry.purity = purity_key
            entry.save()
            used_ids.append(entry.id)
        else:
            created = BalanceEntry.objects.create(
                title=title,
                balance_type=BalanceEntry.BalanceType.GOLD,
                bank=None,
                currency_id=gold_currency.id,
                purity=purity_key,
                amount=amount,
                notes="",
            )
            used_ids.append(created.id)

    balance_qs.exclude(id__in=used_ids).delete()




def _refresh_all_gold_assets_from_live_prices():
    latest_gold = _latest_gold_price()
    if latest_gold is None:
        return

    gold_assets = FixedAsset.objects.filter(asset_type__in=GOLD_ASSET_TYPES).select_related("gold_details")
    for asset in gold_assets:
        details = getattr(asset, "gold_details", None)
        if details is None:
            continue
        _refresh_gold_asset_pricing(asset, details, latest_gold)

    _sync_gold_balance_from_assets()




def _clear_non_selected_asset_details(asset):
    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES and hasattr(asset, "real_estate"):
        asset.real_estate.delete()

    if asset.asset_type not in VEHICLE_ASSET_TYPES and hasattr(asset, "vehicle_details"):
        asset.vehicle_details.delete()

    if asset.asset_type not in GOLD_ASSET_TYPES and hasattr(asset, "gold_details"):
        asset.gold_details.delete()

    if asset.asset_type not in OTHER_ASSET_TYPES and hasattr(asset, "other_asset_details"):
        asset.other_asset_details.delete()




def _sync_vehicle_details(asset, details_data):
    if asset.asset_type not in VEHICLE_ASSET_TYPES or not details_data:
        if hasattr(asset, "vehicle_details"):
            asset.vehicle_details.delete()
        return

    VehicleDetails.objects.update_or_create(
        asset=asset,
        defaults={
            "brand": details_data.get("brand", ""),
            "model": details_data.get("model", ""),
            "year": details_data.get("year") or None,
            "vin": details_data.get("vin", ""),
            "engine": details_data.get("engine", ""),
            "transmission": details_data.get("transmission", ""),
            "fuel_type": details_data.get("fuel_type", ""),
            "mileage": details_data.get("mileage", 0),
            "plate_number": details_data.get("plate_number", ""),
            "license_expiry_date": _parse_iso_date(details_data.get("license_expiry_date")),
            "color": details_data.get("color", ""),
        },
    )




def _sync_gold_details(asset, details_data):
    if asset.asset_type not in GOLD_ASSET_TYPES or not details_data:
        if hasattr(asset, "gold_details"):
            asset.gold_details.delete()
        return

    details_obj, _ = GoldDetails.objects.update_or_create(
        asset=asset,
        defaults={
            "gold_type": details_data.get("gold_type", ""),
            "purity": _normalize_gold_purity(details_data.get("purity", "")),
            "weight": details_data.get("weight", 0),
            "unit": details_data.get("unit", "gram"),
            "cashback_per_gram": _gold_cashback_per_gram(details_data.get("purity", "")),
            "purchase_weight": details_data.get("purchase_weight", 0),
        },
    )

    _refresh_gold_asset_pricing(asset, details_obj)




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




def _sync_asset_maintenance(asset, items):
    AssetMaintenance.objects.filter(asset=asset).delete()
    if asset.asset_type not in VEHICLE_ASSET_TYPES:
        return

    for item in items or []:
        if not item.get("date"):
            continue
        AssetMaintenance.objects.create(
            asset=asset,
            date=item.get("date"),
            maintenance_type=item.get("type", ""),
            cost=item.get("cost", 0),
            notes=item.get("notes", ""),
        )




def _sync_asset_insurance(asset, items):
    AssetInsurance.objects.filter(asset=asset).delete()
    if asset.asset_type not in VEHICLE_ASSET_TYPES:
        return

    for item in items or []:
        if not item.get("company"):
            continue
        AssetInsurance.objects.create(
            asset=asset,
            company=item.get("company", ""),
            policy_number=item.get("policy_number", ""),
            expiry_date=item.get("expiry_date") or None,
            premium=item.get("premium", 0),
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




def _sync_asset_furniture(asset, items):
    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES:
        AssetFurniture.objects.filter(asset=asset).delete()
        return

    AssetFurniture.objects.filter(asset=asset).delete()
    for item in items or []:
        if not item.get("name"):
            continue
        AssetFurniture.objects.create(
            asset=asset,
            name=item.get("name", ""),
            category=item.get("category", ""),
            purchase_date=item.get("purchase_date") or None,
            amount_egp=item.get("amount_egp", 0),
            usd_rate=item.get("usd_rate", 0),
            amount_usd=item.get("amount_usd", 0),
            quantity=item.get("quantity", 1),
            notes=item.get("notes", ""),
        )




def _sync_asset_valuation_history(asset, items):
    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES and asset.asset_type not in VEHICLE_ASSET_TYPES and asset.asset_type not in OTHER_ASSET_TYPES:
        AssetValuationHistory.objects.filter(asset=asset).delete()
        return

    AssetValuationHistory.objects.filter(asset=asset).delete()
    created_items = []
    for item in items or []:
        if not item.get("valuation_date"):
            continue
        created_items.append(
            AssetValuationHistory.objects.create(
                asset=asset,
                valuation_date=item.get("valuation_date"),
                market_value=item.get("market_value", 0),
                valuation_source=item.get("valuation_source", "Manual"),
                notes=item.get("notes", ""),
            )
        )

    if created_items:
        latest_item = max(created_items, key=lambda value: value.valuation_date)
        asset.current_market_value = latest_item.market_value
        asset.last_valuation_date = latest_item.valuation_date
        asset.valuation_source = latest_item.valuation_source
        asset.save()




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




def _resolve_sale_deposit_values(data, existing_sale=None):
    fallback_currency_id = _default_egp_currency_id()

    existing_currency_id = existing_sale.deposit_currency_id if existing_sale else None
    currency_id = data.get("deposit_currency_id", existing_currency_id or fallback_currency_id)
    if not _asset_payment_currency_required(currency_id):
        raise ValueError("currency_required")

    existing_method = existing_sale.deposit_method if existing_sale else ASSET_PAYMENT_METHOD_CASH
    method = _normalize_asset_payment_method(data.get("deposit_method", existing_method))

    existing_bank_id = existing_sale.deposit_bank_id if existing_sale else None
    bank_id = data.get("deposit_bank_id", existing_bank_id)
    if _asset_payment_requires_bank(method) and not bank_id:
        raise ValueError("bank_account_required")
    if method == ASSET_PAYMENT_METHOD_CASH:
        bank_id = None

    return {
        "deposit_currency_id": int(currency_id),
        "deposit_method": method,
        "deposit_bank_id": int(bank_id) if bank_id else None,
    }




def _sale_payment_row(sale):
    currency_id = sale.deposit_currency_id or _default_egp_currency_id()
    method = _normalize_asset_payment_method(sale.deposit_method or ASSET_PAYMENT_METHOD_CASH)
    bank_id = sale.deposit_bank_id if _asset_payment_requires_bank(method) else None
    return {
        "currency_id": currency_id,
        "payment_method": method,
        "bank_id": bank_id,
        "amount": _to_decimal(sale.net_sale_amount),
    }




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



@method_decorator(csrf_exempt, name="dispatch")
class FixedAssetPhotoView(View):

    def post(self, request, pk):

        asset = get_object_or_404(FixedAsset, pk=pk)

        files = request.FILES.getlist("photos")

        if not files:
            return JsonResponse(
                {"error": "No photos uploaded"},
                status=400,
            )

        uploaded = []

        for file in files:

            photo = AssetPhoto.objects.create(
                asset=asset,
                image_data=file.read(),
                filename=file.name,
                mime_type=file.content_type,
            )

            uploaded.append(photo.to_dict())

        return JsonResponse(uploaded, safe=False)

    def delete(self, request, pk, photo_id):

        photo = get_object_or_404(
            AssetPhoto,
            pk=photo_id,
            asset_id=pk,
        )

        photo.delete()

        return JsonResponse({"deleted": True})



class AssetPhotoView(View):

    def get(self, request, photo_id):

        photo = get_object_or_404(
            AssetPhoto,
            pk=photo_id,
        )

        return HttpResponse(
            photo.image_data,
            content_type=photo.mime_type,
        )




def _document_validation_error_response(exc):
    if hasattr(exc, "messages") and exc.messages:
        message = str(exc.messages[0])
    else:
        message = str(exc)
    return JsonResponse({"error": message}, status=400)




def _document_database_error_response(exc):
    message = str(exc or "")
    if "no such table" in message.lower() and "core_document" in message.lower():
        return JsonResponse(
            {"error": "documents_schema_missing", "detail": "Run database migrations to enable document management."},
            status=503,
        )
    return JsonResponse({"error": "documents_unavailable"}, status=503)




@method_decorator(csrf_exempt, name="dispatch")
class DocumentListUploadView(View):
    service = DocumentService()

    def get(self, request, parent_type, parent_id):
        try:
            docs = self.service.list_documents(parent_type, parent_id)
            return JsonResponse({"documents": docs})
        except ValidationError as exc:
            return _document_validation_error_response(exc)
        except (OperationalError, ProgrammingError) as exc:
            return _document_database_error_response(exc)

    def post(self, request, parent_type, parent_id):
        uploaded_file = request.FILES.get("file")
        category = request.POST.get("document_category")
        notes = request.POST.get("notes", "")

        try:
            item = self.service.upload_document(
                parent_type=parent_type,
                parent_id=parent_id,
                uploaded_file=uploaded_file,
                uploaded_by=request.user,
                category=category,
                notes=notes,
            )
            return JsonResponse(item, status=201)
        except ValidationError as exc:
            return _document_validation_error_response(exc)
        except (OperationalError, ProgrammingError) as exc:
            return _document_database_error_response(exc)




@method_decorator(csrf_exempt, name="dispatch")
class DocumentFileView(View):
    service = DocumentService()

    def get(self, request, document_id):
        try:
            metadata, content = self.service.get_document_content(document_id)
        except (OperationalError, ProgrammingError) as exc:
            return _document_database_error_response(exc)
        if metadata is None:
            return JsonResponse({"error": "document_not_found"}, status=404)

        disposition = request.GET.get("disposition", "inline").strip().lower()
        if disposition not in {"inline", "attachment"}:
            disposition = "inline"

        response = HttpResponse(content, content_type=metadata.get("mime_type") or "application/octet-stream")
        response["Content-Disposition"] = f'{disposition}; filename="{metadata.get("original_file_name", "document")}"'
        response["Content-Length"] = str(metadata.get("file_size", len(content)))
        return response

    def put(self, request, document_id):
        doc = self.service.get_document(document_id)
        if doc is None:
            return JsonResponse({"error": "document_not_found"}, status=404)

        uploaded_file = request.FILES.get("file")
        category = request.POST.get("document_category") if "document_category" in request.POST else None
        notes = request.POST.get("notes") if "notes" in request.POST else None

        try:
            item = self.service.replace_document(
                document_id=document_id,
                uploaded_file=uploaded_file,
                uploaded_by=request.user,
                category=category,
                notes=notes,
            )
            return JsonResponse(item)
        except ValidationError as exc:
            return _document_validation_error_response(exc)
        except (OperationalError, ProgrammingError) as exc:
            return _document_database_error_response(exc)

    def post(self, request, document_id):
        return self.put(request, document_id)

    def delete(self, request, document_id):
        try:
            deleted = self.service.delete_document(document_id)
        except (OperationalError, ProgrammingError) as exc:
            return _document_database_error_response(exc)
        if not deleted:
            return JsonResponse({"error": "document_not_found"}, status=404)
        return JsonResponse({"deleted": True})




@method_decorator(csrf_exempt, name="dispatch")
class DocumentCategoriesView(View):
    service = DocumentService()

    def get(self, request):
        parent_type = request.GET.get("parent_type", "")
        try:
            categories = self.service.categories_for_parent(parent_type)
            return JsonResponse({"categories": categories})
        except ValidationError as exc:
            return _document_validation_error_response(exc)
        except (OperationalError, ProgrammingError) as exc:
            return _document_database_error_response(exc)
    


@method_decorator(csrf_exempt, name="dispatch")
class AssetRenovationListView(View):

    def get(self, request):
        asset_id = request.GET.get("asset")

        qs = AssetRenovation.objects.all().order_by("date", "id")

        if asset_id:
            qs = qs.filter(asset_id=asset_id)

        return JsonResponse({
            "renovations": [r.to_dict() for r in qs]
        })

    def post(self, request):
        data = json.loads(request.body)

        item = AssetRenovation.objects.create(
            asset_id=data["asset_id"],
            date=data["date"],
            category=data["category"],
            description=data.get("description", ""),
            amount_egp=data.get("amount_egp", 0),
            usd_rate=data.get("usd_rate", 0),
            amount_usd=data.get("amount_usd", 0),
            notes=data.get("notes", ""),
        )

        return JsonResponse(item.to_dict(), status=201)



@method_decorator(csrf_exempt, name="dispatch")
class AssetRenovationDetailView(View):

    def put(self, request, pk):
        item = get_object_or_404(AssetRenovation, pk=pk)

        data = json.loads(request.body)

        fields = [
            "date",
            "category",
            "description",
            "amount_egp",
            "usd_rate",
            "amount_usd",
            "notes",
        ]

        for field in fields:
            if field in data:
                setattr(item, field, data[field])

        item.save()

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(AssetRenovation, pk=pk)
        item.delete()

        return JsonResponse({"deleted": pk})




@method_decorator(csrf_exempt, name="dispatch")
class AssetMaintenanceListView(View):

    def get(self, request):
        asset_id = request.GET.get("asset")

        qs = AssetMaintenance.objects.all().order_by("date", "id")

        if asset_id:
            qs = qs.filter(asset_id=asset_id)

        return JsonResponse({
            "maintenance": [m.to_dict() for m in qs]
        })

    def post(self, request):
        data = json.loads(request.body)

        item = AssetMaintenance.objects.create(
            asset_id=data["asset_id"],
            date=data["date"],
            maintenance_type=data["maintenance_type"],
            cost=data.get("cost", 0),
            notes=data.get("notes", ""),
        )

        return JsonResponse(item.to_dict(), status=201)




@method_decorator(csrf_exempt, name="dispatch")
class AssetMaintenanceDetailView(View):

    def put(self, request, pk):
        item = get_object_or_404(AssetMaintenance, pk=pk)

        data = json.loads(request.body)

        fields = ["date", "maintenance_type", "cost", "notes"]

        for field in fields:
            if field in data:
                setattr(item, field, data[field])

        item.save()

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(AssetMaintenance, pk=pk)
        item.delete()

        return JsonResponse({"deleted": pk})




@method_decorator(csrf_exempt, name="dispatch")
class AssetInsuranceListView(View):

    def get(self, request):
        asset_id = request.GET.get("asset")

        qs = AssetInsurance.objects.all().order_by("expiry_date", "id")

        if asset_id:
            qs = qs.filter(asset_id=asset_id)

        return JsonResponse({
            "insurance": [i.to_dict() for i in qs]
        })

    def post(self, request):
        data = json.loads(request.body)

        item = AssetInsurance.objects.create(
            asset_id=data["asset_id"],
            company=data["company"],
            policy_number=data.get("policy_number", ""),
            expiry_date=data.get("expiry_date") or None,
            premium=data.get("premium", 0),
        )

        return JsonResponse(item.to_dict(), status=201)




@method_decorator(csrf_exempt, name="dispatch")
class AssetInsuranceDetailView(View):

    def put(self, request, pk):
        item = get_object_or_404(AssetInsurance, pk=pk)

        data = json.loads(request.body)

        fields = ["company", "policy_number", "expiry_date", "premium"]

        for field in fields:
            if field in data:
                setattr(item, field, data[field])

        item.save()

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(AssetInsurance, pk=pk)
        item.delete()

        return JsonResponse({"deleted": pk})
    


@method_decorator(csrf_exempt, name="dispatch")
class AssetFurnitureListView(View):

    def get(self, request):
        asset_id = request.GET.get("asset")

        qs = AssetFurniture.objects.all().order_by("name")

        if asset_id:
            qs = qs.filter(asset_id=asset_id)

        return JsonResponse({
            "furniture": [f.to_dict() for f in qs]
        })

    def post(self, request):
        data = json.loads(request.body)

        item = AssetFurniture.objects.create(
            asset_id=data["asset_id"],
            name=data["name"],
            category=data.get("category", ""),
            purchase_date=data.get("purchase_date") or None,
            amount_egp=data.get("amount_egp", 0),
            usd_rate=data.get("usd_rate", 0),
            amount_usd=data.get("amount_usd", 0),
            quantity=data.get("quantity", 1),
            notes=data.get("notes", ""),
        )

        return JsonResponse(item.to_dict(), status=201)




@method_decorator(csrf_exempt, name="dispatch")
class AssetFurnitureDetailView(View):

    def put(self, request, pk):
        item = get_object_or_404(AssetFurniture, pk=pk)

        data = json.loads(request.body)

        fields = [
            "name",
            "category",
            "purchase_date",
            "amount_egp",
            "usd_rate",
            "amount_usd",
            "quantity",
            "notes",
        ]

        for field in fields:
            if field in data:
                setattr(item, field, data[field])

        item.save()

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(AssetFurniture, pk=pk)
        item.delete()

        return JsonResponse({"deleted": pk})



@method_decorator(csrf_exempt, name="dispatch")
class AssetValuationHistoryListView(View):

    def get(self, request):
        asset_id = request.GET.get("asset")

        qs = AssetValuationHistory.objects.all().order_by(
            "-valuation_date",
            "-id",
        )

        if asset_id:
            qs = qs.filter(asset_id=asset_id)

        return JsonResponse({
            "valuation_history": [
                v.to_dict() for v in qs
            ]
        })

    def post(self, request):
        data = json.loads(request.body)

        item = AssetValuationHistory.objects.create(
            asset_id=data["asset_id"],
            valuation_date=data["valuation_date"],
            market_value=data["market_value"],
            valuation_source=data.get(
                "valuation_source",
                "Manual",
            ),
            notes=data.get("notes", ""),
        )

        asset = item.asset
        asset.current_market_value = item.market_value
        asset.last_valuation_date = item.valuation_date
        asset.valuation_source = item.valuation_source
        asset.save()

        return JsonResponse(item.to_dict(), status=201)




@method_decorator(csrf_exempt, name="dispatch")
class AssetValuationHistoryDetailView(View):

    def put(self, request, pk):
        item = get_object_or_404(
            AssetValuationHistory,
            pk=pk,
        )

        data = json.loads(request.body)

        fields = [
            "valuation_date",
            "market_value",
            "valuation_source",
            "notes",
        ]

        for field in fields:
            if field in data:
                setattr(item, field, data[field])

        item.save()

        asset = item.asset
        asset.current_market_value = item.market_value
        asset.last_valuation_date = item.valuation_date
        asset.valuation_source = item.valuation_source
        asset.save()

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(
            AssetValuationHistory,
            pk=pk,
        )
        item.delete()

        return JsonResponse({"deleted": pk})



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


