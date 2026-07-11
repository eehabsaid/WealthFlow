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


