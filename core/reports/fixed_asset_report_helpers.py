# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
import datetime
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from core.models import FixedAsset
from core.services.balance.net_worth_service import NetWorthService
from core.utils.date_formatter import format_date
from core.reports.report_utils import get_translations, format_arabic, get_text

def fixed_asset_report_queryset():
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
        .all()
    )

def fixed_asset_report_context(request):
    lang = request.GET.get("lang", "en")
    t = get_translations(lang)
    asset_id = request.GET.get("asset_id")

    qs = fixed_asset_report_queryset()
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
        net_worth_service = NetWorthService()
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

def fixed_asset_user_text(value, lang):
    if not value or str(value).strip() in ("", "None"):
        return "-"
    return format_arabic(value) if lang == "ar" else str(value)

def fixed_asset_pdf_table(rows, col_widths, font_name):
    style = TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1f2937")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
    )
    formatted_rows = []
    for row in rows:
        formatted_row = []
        for item in row:
            if isinstance(item, Paragraph):
                formatted_row.append(item)
            else:
                formatted_row.append(str(item))
        formatted_rows.append(formatted_row)
    return Table(formatted_rows, colWidths=col_widths, style=style)

def build_fixed_asset_pdf_story(asset, lang, t, styles, title_style, heading_style, body_style, font_name):
    data = asset.to_dict()
    story = []

    story.append(Paragraph(f"{fixed_asset_report_label(t, lang, 'asset_details', 'Asset Details')}: {fixed_asset_user_text(asset.name, lang)}", heading_style))

    basic_rows = [
        [fixed_asset_report_label(t, lang, "asset_name", "Asset Name"), fixed_asset_user_text(data.get("name"), lang)],
        [fixed_asset_report_label(t, lang, "asset_type", "Asset Type"), fixed_asset_report_label(t, lang, data.get("asset_type"), data.get("asset_type"))],
        [fixed_asset_report_label(t, lang, "status", "Status"), fixed_asset_report_label(t, lang, data.get("status"), data.get("status"))],
        [fixed_asset_report_label(t, lang, "purchase_date", "Purchase Date"), fixed_asset_display_value(data.get("purchase_date"), lang)],
        [fixed_asset_report_label(t, lang, "purchase_price_egp", "Purchase Price (EGP)"), f"{float(data.get('purchase_price') or 0):,.2f}"],
        [fixed_asset_report_label(t, lang, "total_investment_egp", "Total Investment (EGP)"), f"{float(data.get('total_investment') or data.get('purchase_price') or 0):,.2f}"],
        [fixed_asset_report_label(t, lang, "current_market_value", "Current Market Value"), f"{float(data.get('current_market_value') or 0):,.2f}"],
        [fixed_asset_report_label(t, lang, "gain_loss", "Gain / Loss"), f"{float(data.get('gain_loss') or 0):,.2f}"],
        [fixed_asset_report_label(t, lang, "notes", "Notes"), fixed_asset_user_text(data.get("notes"), lang)],
    ]
    story.append(fixed_asset_pdf_table(basic_rows, [5 * cm, 10.5 * cm], font_name))
    story.append(Spacer(1, 0.3 * cm))

    def append_collection(section_label, collection_data, headers_and_keys, item_row_builder):
        if not collection_data:
            return
        story.append(Paragraph(section_label, heading_style))
        header_row = [title for _, title in headers_and_keys]
        rows = [header_row]
        for item in collection_data:
            rows.append(item_row_builder(item))
        widths = [15.5 * cm / len(headers_and_keys)] * len(headers_and_keys)
        story.append(fixed_asset_pdf_table(rows, widths, font_name))
        story.append(Spacer(1, 0.3 * cm))

    append_collection(
        fixed_asset_report_label(t, lang, "acquisition_costs", "Acquisition Costs"),
        data.get("acquisition_costs") or [],
        [("date", fixed_asset_report_label(t, lang, "date", "Date")), ("category", fixed_asset_report_label(t, lang, "category", "Category")), ("amount_egp", fixed_asset_report_label(t, lang, "amount_egp", "Amount EGP")), ("notes", fixed_asset_report_label(t, lang, "notes", "Notes"))],
        lambda item: [
            fixed_asset_display_value(item.get("date")),
            fixed_asset_user_text(item.get("category"), lang),
            f"{float(item.get('amount_egp') or 0):,.2f}",
            fixed_asset_user_text(item.get("notes"), lang),
        ],
    )

    append_collection(
        fixed_asset_report_label(t, lang, "renovations", "Renovations"),
        data.get("renovations") or [],
        [("date", fixed_asset_report_label(t, lang, "date", "Date")), ("category", fixed_asset_report_label(t, lang, "category", "Category")), ("amount_egp", fixed_asset_report_label(t, lang, "amount_egp", "Amount EGP")), ("notes", fixed_asset_report_label(t, lang, "notes", "Notes"))],
        lambda item: [
            fixed_asset_display_value(item.get("date")),
            fixed_asset_user_text(item.get("category"), lang),
            f"{float(item.get('amount_egp') or 0):,.2f}",
            fixed_asset_user_text(item.get("notes"), lang),
        ],
    )

    append_collection(
        fixed_asset_report_label(t, lang, "furniture", "Furniture"),
        data.get("furniture") or [],
        [("name", fixed_asset_report_label(t, lang, "asset_name", "Item")), ("category", fixed_asset_report_label(t, lang, "category", "Category")), ("purchase_date", fixed_asset_report_label(t, lang, "purchase_date", "Purchase Date")), ("amount_egp", fixed_asset_report_label(t, lang, "amount_egp", "Amount EGP")), ("notes", fixed_asset_report_label(t, lang, "notes", "Notes"))],
        lambda item: [
            fixed_asset_user_text(item.get("name"), lang),
            fixed_asset_user_text(item.get("category"), lang),
            fixed_asset_display_value(item.get("purchase_date")),
            f"{float(item.get('amount_egp') or 0):,.2f}",
            fixed_asset_user_text(item.get("notes"), lang),
        ],
    )

    append_collection(
        fixed_asset_report_label(t, lang, "valuation_history", "Valuation History"),
        data.get("valuation_history") or [],
        [("date", fixed_asset_report_label(t, lang, "date", "Date")), ("current_market_value", fixed_asset_report_label(t, lang, "current_market_value", "Market Value")), ("valuation_source", fixed_asset_report_label(t, lang, "valuation_source", "Source")), ("notes", fixed_asset_report_label(t, lang, "notes", "Notes"))],
        lambda item: [
            fixed_asset_display_value(item.get("valuation_date")),
            f"{float(item.get('market_value') or 0):,.2f}",
            fixed_asset_user_text(item.get("valuation_source"), lang),
            fixed_asset_user_text(item.get("notes"), lang),
        ],
    )

    sale = data.get("sale") or None
    if sale:
        sale_rows = [
            [fixed_asset_report_label(t, lang, "sale_date", "Sale Date"), fixed_asset_display_value(sale.get("sale_date"))],
            [fixed_asset_report_label(t, lang, "sale_price_egp", "Sale Price (EGP)"), f"{float(sale.get('sale_price') or 0):,.2f}"],
            [fixed_asset_report_label(t, lang, "selling_expenses_egp", "Selling Expenses (EGP)"), f"{float(sale.get('selling_expenses') or 0):,.2f}"],
            [fixed_asset_report_label(t, lang, "net_sale_amount", "Net Sale Amount"), f"{float(sale.get('net_sale_amount') or 0):,.2f}"],
            [fixed_asset_report_label(t, lang, "deposit_balance", "Deposit Balance"), fixed_asset_display_value(sale.get("deposit_balance_id"))],
            [fixed_asset_report_label(t, lang, "notes", "Notes"), fixed_asset_user_text(sale.get("notes"), lang)],
        ]
        story.append(Paragraph(fixed_asset_report_label(t, lang, "sale_information", "Sale Information"), heading_style))
        story.append(fixed_asset_pdf_table(sale_rows, [5 * cm, 10.5 * cm], font_name))
        story.append(Spacer(1, 0.3 * cm))

    return story
