# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from core.models import PAGE_PERMISSION_CHOICES

# Re-exported Report Helper Functions & Classes
from core.reports.report_utils import (
    month_sort_key,
    get_translations,
    format_arabic,
    get_text,
)
from core.reports.fixed_asset_report_helpers import (
    fixed_asset_report_queryset as _fixed_asset_report_queryset,
    fixed_asset_report_context as _fixed_asset_report_context,
    fixed_asset_display_value as _fixed_asset_display_value,
    fixed_asset_report_label as _fixed_asset_report_label,
    fixed_asset_user_text as _fixed_asset_user_text,
    fixed_asset_pdf_table as _fixed_asset_pdf_table,
    build_fixed_asset_pdf_story as _build_fixed_asset_pdf_story,
)

# Re-exported Report Classes
from core.reports.excel_workbook_generator import ExportExcelWorkbookGenerator
from core.reports.generate_report_generator import GenerateReportGenerator
from core.reports.salary_report_view import SalaryReportView
from core.reports.balance_report_view import BalanceReportView
from core.reports.certificate_report_view import CertificateReportView
from core.reports.fixed_asset_pdf_report_generator import FixedAssetPdfReportGenerator
from core.reports.fixed_asset_excel_report_generator import FixedAssetExcelReportGenerator

__all__ = [
    "ExportExcelWorkbookGenerator",
    "GenerateReportGenerator",
    "SalaryReportView",
    "BalanceReportView",
    "CertificateReportView",
    "FixedAssetPdfReportGenerator",
    "FixedAssetExcelReportGenerator",
    "month_sort_key",
    "get_translations",
    "format_arabic",
    "get_text",
    "export_excel",
    "_fixed_asset_report_queryset",
    "_fixed_asset_report_context",
    "_fixed_asset_display_value",
    "_fixed_asset_report_label",
    "_fixed_asset_user_text",
    "_fixed_asset_pdf_table",
    "_build_fixed_asset_pdf_story",
]

User = get_user_model()
PAGE_PERMISSION_KEYS = [key for key, _ in PAGE_PERMISSION_CHOICES]

REAL_ESTATE_ASSET_TYPES = {"Real Estate"}
VEHICLE_ASSET_TYPES = {"Vehicles"}
GOLD_ASSET_TYPES = {"Gold"}
OTHER_ASSET_TYPES = {"Other Assets"}

ASSET_PAYMENT_METHOD_CASH = "Cash"
ASSET_PAYMENT_METHOD_CARD = "Card"
ASSET_PAYMENT_METHOD_BANK = "Bank"
ASSET_PAYMENT_METHOD_BANK_TRANSFER = "Bank Transfer"

ASSET_PAYMENT_METHOD_NORMALIZED = {
    "cash": ASSET_PAYMENT_METHOD_CASH,
    "card": ASSET_PAYMENT_METHOD_CARD,
    "bank": ASSET_PAYMENT_METHOD_BANK,
    "bank transfer": ASSET_PAYMENT_METHOD_BANK_TRANSFER,
    "bank_transfer": ASSET_PAYMENT_METHOD_BANK_TRANSFER,
}

GOLD_UNIT_TO_GRAMS = {
    "g": Decimal("1"),
    "gm": Decimal("1"),
    "gram": Decimal("1"),
    "grams": Decimal("1"),
    "kg": Decimal("1000"),
    "kilogram": Decimal("1000"),
    "kilograms": Decimal("1000"),
    "oz": Decimal("31.1034768"),
    "ounce": Decimal("31.1034768"),
    "ounces": Decimal("31.1034768"),
    "tola": Decimal("11.6638038"),
}

def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)
    return None

@login_required
def export_excel(request):
    """Generate and download the full Balance tracker Excel workbook."""
    from core.reports.excel_generator import generate_excel
    from datetime import date

    buf = generate_excel()
    filename = f"Balance_Tracker_{date.today().strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response