# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
"""
Fixed-asset report queryset/context building and value formatting.

Split out of the former monolithic fixed_asset_report_helpers.py
(200-line rule).
"""

import datetime
from core.models import FixedAsset
from core.services.balance.net_worth_service import NetWorthService
from core.utils.date_formatter import format_date
from core.reports.report_utils import get_translations, get_text
from core.reports.report_context import set_report_base_code
from core.reports.pdf_font_utils import process_pdf_text
from core.services.shared.base_currency import get_user_base_code


def fixed_asset_report_queryset(owner):
    return (
        FixedAsset.objects.select_related(
            "vehicle_details",
            "gold_details",
            "other_asset_details",
            "mortgage",
            "rental",
            "sale",
            "real_estate",
        )
        .prefetch_related(
            "acquisition_costs",
            "renovations",
            "furniture",
            "valuation_history",
            "photos",
        )
        .filter(owner=owner)
    )


def fixed_asset_report_context(request):
    set_report_base_code(get_user_base_code(request.user))
    lang = request.GET.get("lang", "en")
    t = get_translations(lang)
    asset_id = request.GET.get("asset_id")

    qs = fixed_asset_report_queryset(request.user)
    if asset_id:
        try:
            asset_obj = qs.get(id=int(asset_id))
            return {
                "lang": lang,
                "t": t,
                "assets": [asset_obj],
                "scope": "single",
                "portfolio_snapshot": None,
            }
        except (ValueError, TypeError):
            raise ValueError("Invalid asset_id format")
    else:
        assets = list(qs)
        if not assets:
            raise FixedAsset.DoesNotExist("No fixed assets found")
        net_worth_service = NetWorthService(request.user)
        portfolio_snapshot = net_worth_service.fixed_assets_snapshot()
        return {
            "lang": lang,
            "t": t,
            "assets": assets,
            "scope": "portfolio",
            "portfolio_snapshot": portfolio_snapshot,
        }


def fixed_asset_display_value(value, lang="en"):
    if value is None or str(value).strip() in ("", "None"):
        return "-"
    if isinstance(value, (datetime.date, datetime.datetime)):
        return format_date(value, lang)
    if isinstance(value, bool):
        return get_text("yes" if value else "no", lang, get_translations(lang), "Yes" if value else "No")
    return str(value)


def fixed_asset_report_label(t, lang, key, default):
    return get_text(key, lang, t, default)


def fixed_asset_user_text(value, lang="en"):
    if not value or str(value).strip() in ("", "None"):
        return "-"
    return process_pdf_text(value)
