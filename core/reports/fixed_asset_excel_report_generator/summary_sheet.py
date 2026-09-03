# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false
from core.reports.fixed_asset_report_helpers import fixed_asset_report_label as _fixed_asset_report_label


def build_summary_sheet(wb, lang, t, assets, scope, portfolio_snapshot, header_font):
    summary_ws = wb.active
    if summary_ws is None:
        summary_ws = wb.create_sheet(title="Summary")
    else:
        summary_ws.title = "Summary"

    if lang == "ar":
        try:
            summary_ws.sheet_view.rightToLeft = True
        except Exception:
            pass

    summary_headers = [
        _fixed_asset_report_label(t, lang, "asset_name", "Asset Name"),
        _fixed_asset_report_label(t, lang, "asset_type", "Asset Type"),
        _fixed_asset_report_label(t, lang, "status", "Status"),
        _fixed_asset_report_label(t, lang, "purchase_date", "Purchase Date"),
        _fixed_asset_report_label(t, lang, "purchase_price_egp", "Purchase Price (EGP)"),
        _fixed_asset_report_label(t, lang, "total_investment_egp", "Total Investment (EGP)"),
        _fixed_asset_report_label(t, lang, "current_market_value", "Current Market Value"),
        _fixed_asset_report_label(t, lang, "gain_loss", "Gain / Loss"),
        _fixed_asset_report_label(t, lang, "country", "Country"),
        _fixed_asset_report_label(t, lang, "city", "City"),
        _fixed_asset_report_label(t, lang, "address", "Address"),
        _fixed_asset_report_label(t, lang, "sale_date", "Sale Date"),
        _fixed_asset_report_label(t, lang, "net_sale_amount", "Net Sale Amount"),
        _fixed_asset_report_label(t, lang, "notes", "Notes"),
    ]
    summary_ws.append(summary_headers)
    for cell in summary_ws[1]:
        cell.font = header_font

    for asset in assets:
        data = asset.to_dict()
        real_estate = data.get("real_estate") or {}
        sale = data.get("sale") or {}
        summary_ws.append(
            [
                data.get("name"),
                data.get("asset_type"),
                data.get("status"),
                data.get("purchase_date"),
                float(data.get("purchase_price") or 0),
                float(data.get("total_investment") or data.get("purchase_price") or 0),
                float(data.get("current_market_value") or 0),
                float(data.get("gain_loss") or 0),
                real_estate.get("country"),
                real_estate.get("city"),
                real_estate.get("address"),
                sale.get("sale_date"),
                float(sale.get("net_sale_amount") or 0),
                data.get("notes"),
            ]
        )

    if scope == "portfolio":
        summary_ws.append([])
        summary_ws.append([
            _fixed_asset_report_label(t, lang, "total_fixed_assets_value", "Total Fixed Assets"),
            float(portfolio_snapshot.get("total_fixed_assets_value") or 0),
        ])
        summary_ws.append([
            _fixed_asset_report_label(t, lang, "net_worth", "Net Worth"),
            float(portfolio_snapshot.get("total_net_worth") or 0),
        ])
        summary_ws.append([
            _fixed_asset_report_label(t, lang, "net_worth_contribution", "Net Worth Contribution"),
            float(portfolio_snapshot.get("net_worth_contribution") or 0),
        ])

    return summary_ws
