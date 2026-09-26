# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
"""
Fixed-asset PDF table/story building.

Split out of the former monolithic fixed_asset_report_helpers.py
(200-line rule).
"""

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from core.reports.pdf_font_utils import process_pdf_text
from core.reports.fixed_asset_report_helpers.context import (
    fixed_asset_display_value,
    fixed_asset_report_label,
    fixed_asset_user_text,
)


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
                formatted_row.append(process_pdf_text(str(item) if item is not None else ""))
        formatted_rows.append(formatted_row)
    return Table(formatted_rows, colWidths=col_widths, style=style)


def build_fixed_asset_pdf_story(asset, lang, t, styles, title_style, heading_style, body_style, font_name):
    data = asset.to_dict()
    story = []

    story.append(Paragraph(process_pdf_text(f"{fixed_asset_report_label(t, lang, 'asset_details', 'Asset Details')}: {asset.name}"), heading_style))

    basic_rows = [
        [fixed_asset_report_label(t, lang, "asset_name", "Asset Name"), fixed_asset_user_text(data.get("name"), lang)],
        [fixed_asset_report_label(t, lang, "asset_type", "Asset Type"), fixed_asset_report_label(t, lang, data.get("asset_type"), data.get("asset_type"))],
        [fixed_asset_report_label(t, lang, "status", "Status"), fixed_asset_report_label(t, lang, data.get("status"), data.get("status"))],
        [fixed_asset_report_label(t, lang, "purchase_date", "Purchase Date"), fixed_asset_display_value(data.get("purchase_date"), lang)],
        [fixed_asset_report_label(t, lang, "purchase_price_egp", "Purchase Price ({base})"), f"{float(data.get('purchase_price') or 0):,.2f}"],
        [fixed_asset_report_label(t, lang, "total_investment_egp", "Total Investment ({base})"), f"{float(data.get('total_investment') or data.get('purchase_price') or 0):,.2f}"],
        [fixed_asset_report_label(t, lang, "current_market_value", "Current Market Value"), f"{float(data.get('current_market_value') or 0):,.2f}"],
        [fixed_asset_report_label(t, lang, "gain_loss", "Gain / Loss"), f"{float(data.get('gain_loss') or 0):,.2f}"],
        [fixed_asset_report_label(t, lang, "notes", "Notes"), fixed_asset_user_text(data.get("notes"), lang)],
    ]
    story.append(fixed_asset_pdf_table(basic_rows, [5 * cm, 10.5 * cm], font_name))
    story.append(Spacer(1, 0.3 * cm))

    def append_collection(section_label, collection_data, headers_and_keys, item_row_builder):
        if not collection_data:
            return
        story.append(Paragraph(process_pdf_text(section_label), heading_style))
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
        [("date", fixed_asset_report_label(t, lang, "date", "Date")), ("category", fixed_asset_report_label(t, lang, "category", "Category")), ("amount_egp", fixed_asset_report_label(t, lang, "amount_egp", "Amount ({base})")), ("notes", fixed_asset_report_label(t, lang, "notes", "Notes"))],
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
        [("date", fixed_asset_report_label(t, lang, "date", "Date")), ("category", fixed_asset_report_label(t, lang, "category", "Category")), ("amount_egp", fixed_asset_report_label(t, lang, "amount_egp", "Amount ({base})")), ("notes", fixed_asset_report_label(t, lang, "notes", "Notes"))],
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
        [("name", fixed_asset_report_label(t, lang, "asset_name", "Item")), ("category", fixed_asset_report_label(t, lang, "category", "Category")), ("purchase_date", fixed_asset_report_label(t, lang, "purchase_date", "Purchase Date")), ("amount_egp", fixed_asset_report_label(t, lang, "amount_egp", "Amount ({base})")), ("notes", fixed_asset_report_label(t, lang, "notes", "Notes"))],
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
            [fixed_asset_report_label(t, lang, "sale_price_egp", "Sale Price ({base})"), f"{float(sale.get('sale_price') or 0):,.2f}"],
            [fixed_asset_report_label(t, lang, "selling_expenses_egp", "Selling Expenses ({base})"), f"{float(sale.get('selling_expenses') or 0):,.2f}"],
            [fixed_asset_report_label(t, lang, "net_sale_amount", "Net Sale Amount"), f"{float(sale.get('net_sale_amount') or 0):,.2f}"],
            [fixed_asset_report_label(t, lang, "deposit_balance", "Deposit Balance"), fixed_asset_display_value(sale.get("deposit_balance_id"))],
            [fixed_asset_report_label(t, lang, "notes", "Notes"), fixed_asset_user_text(sale.get("notes"), lang)],
        ]
        story.append(Paragraph(fixed_asset_report_label(t, lang, "sale_information", "Sale Information"), heading_style))
        story.append(fixed_asset_pdf_table(sale_rows, [5 * cm, 10.5 * cm], font_name))
        story.append(Spacer(1, 0.3 * cm))

    return story
