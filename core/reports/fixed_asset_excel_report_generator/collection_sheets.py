# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportUnknownLambdaType=false
from core.reports.fixed_asset_report_helpers import fixed_asset_report_label as _fixed_asset_report_label


def get_collection_definitions(t, lang):
    """
    Each entry: (sheet_name, title, headers, row_builder, collection_getter).
    row_builder(asset_data, item) -> row values.
    collection_getter(asset_data) -> list of items for that asset.
    """
    return [
        (
            "Acquisition Costs",
            _fixed_asset_report_label(t, lang, "acquisition_costs", "Acquisition Costs"),
            [
                _fixed_asset_report_label(t, lang, "asset_name", "Asset Name"),
                _fixed_asset_report_label(t, lang, "date", "Date"),
                _fixed_asset_report_label(t, lang, "category", "Category"),
                _fixed_asset_report_label(t, lang, "amount_egp", "Amount EGP"),
                _fixed_asset_report_label(t, lang, "notes", "Notes"),
            ],
            lambda asset_data, item: [
                asset_data.get("name"),
                item.get("date"),
                item.get("category"),
                float(item.get("amount_egp") or 0),
                item.get("notes"),
            ],
            lambda asset_data: asset_data.get("acquisition_costs") or [],
        ),
        (
            "Renovations",
            _fixed_asset_report_label(t, lang, "renovations", "Renovations"),
            [
                _fixed_asset_report_label(t, lang, "asset_name", "Asset Name"),
                _fixed_asset_report_label(t, lang, "date", "Date"),
                _fixed_asset_report_label(t, lang, "category", "Category"),
                _fixed_asset_report_label(t, lang, "amount_egp", "Amount EGP"),
                _fixed_asset_report_label(t, lang, "notes", "Notes"),
            ],
            lambda asset_data, item: [
                asset_data.get("name"),
                item.get("date"),
                item.get("category"),
                float(item.get("amount_egp") or 0),
                item.get("notes"),
            ],
            lambda asset_data: asset_data.get("renovations") or [],
        ),
        (
            "Furniture",
            _fixed_asset_report_label(t, lang, "furniture", "Furniture"),
            [
                _fixed_asset_report_label(t, lang, "asset_name", "Asset Name"),
                _fixed_asset_report_label(t, lang, "category", "Category"),
                _fixed_asset_report_label(t, lang, "purchase_date", "Purchase Date"),
                _fixed_asset_report_label(t, lang, "amount_egp", "Amount EGP"),
                _fixed_asset_report_label(t, lang, "notes", "Notes"),
            ],
            lambda asset_data, item: [
                item.get("name"),
                item.get("category"),
                item.get("purchase_date"),
                float(item.get("amount_egp") or 0),
                item.get("notes"),
            ],
            lambda asset_data: asset_data.get("furniture") or [],
        ),
        (
            "Valuations",
            _fixed_asset_report_label(t, lang, "valuation_history", "Valuation History"),
            [
                _fixed_asset_report_label(t, lang, "asset_name", "Asset Name"),
                _fixed_asset_report_label(t, lang, "date", "Date"),
                _fixed_asset_report_label(t, lang, "current_market_value", "Market Value"),
                _fixed_asset_report_label(t, lang, "valuation_source", "Valuation Source"),
                _fixed_asset_report_label(t, lang, "notes", "Notes"),
            ],
            lambda asset_data, item: [
                asset_data.get("name"),
                item.get("valuation_date"),
                float(item.get("market_value") or 0),
                item.get("valuation_source"),
                item.get("notes"),
            ],
            lambda asset_data: asset_data.get("valuation_history") or [],
        ),
        (
            "Photos",
            _fixed_asset_report_label(t, lang, "photos", "Photos"),
            [
                _fixed_asset_report_label(t, lang, "asset_name", "Asset Name"),
                _fixed_asset_report_label(t, lang, "description", "Description"),
                _fixed_asset_report_label(t, lang, "notes", "Filename"),
                "URL",
            ],
            lambda asset_data, item: [
                asset_data.get("name"),
                item.get("title"),
                item.get("filename"),
                item.get("url"),
            ],
            lambda asset_data: asset_data.get("photos") or [],
        ),
    ]


def build_collection_sheets(wb, assets, collections, header_font):
    for sheet_name, _title, headers, row_builder, collection_getter in collections:
        ws = wb.create_sheet(title=sheet_name)
        ws.append(headers)
        for cell in ws[1]:
            cell.font = header_font
        for asset in assets:
            asset_data = asset.to_dict()
            for item in collection_getter(asset_data):
                ws.append(row_builder(asset_data, item))
