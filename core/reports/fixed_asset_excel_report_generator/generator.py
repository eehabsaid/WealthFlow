# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false
import openpyxl
from django.http import JsonResponse
from openpyxl.styles import Font

from core.models import FixedAsset
from core.reports.fixed_asset_excel_report_generator.collection_sheets import (
    build_collection_sheets,
    get_collection_definitions,
)
from core.reports.fixed_asset_excel_report_generator.formatting import autofit_columns, build_xlsx_response
from core.reports.fixed_asset_excel_report_generator.sale_sheet import build_sale_sheet
from core.reports.fixed_asset_excel_report_generator.summary_sheet import build_summary_sheet
from core.reports.fixed_asset_report_helpers import fixed_asset_report_context as _fixed_asset_report_context


class FixedAssetExcelReportGenerator(object):

    def get(self, request):
        try:
            context = _fixed_asset_report_context(request)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        except FixedAsset.DoesNotExist:
            return JsonResponse({"error": "No fixed assets found"}, status=404)

        lang = context["lang"]
        t = context["t"]
        assets = context["assets"]
        scope = context["scope"]
        portfolio_snapshot = context.get("portfolio_snapshot") or {}

        wb = openpyxl.Workbook()
        header_font = Font(bold=True)

        build_summary_sheet(wb, lang, t, assets, scope, portfolio_snapshot, header_font)
        build_sale_sheet(wb, lang, t, assets, header_font)

        collections = get_collection_definitions(t, lang)
        build_collection_sheets(wb, assets, collections, header_font)

        autofit_columns(wb)

        return build_xlsx_response(wb, assets, scope)
