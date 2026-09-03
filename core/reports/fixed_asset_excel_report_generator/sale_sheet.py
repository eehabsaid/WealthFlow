# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false
from core.reports.fixed_asset_report_helpers import fixed_asset_report_label as _fixed_asset_report_label


def build_sale_sheet(wb, lang, t, assets, header_font):
    sale_ws = wb.create_sheet(title="Sale")
    sale_headers = [
        _fixed_asset_report_label(t, lang, "asset_name", "Asset Name"),
        _fixed_asset_report_label(t, lang, "sale_date", "Sale Date"),
        _fixed_asset_report_label(t, lang, "sale_price_egp", "Sale Price (EGP)"),
        _fixed_asset_report_label(t, lang, "selling_expenses_egp", "Selling Expenses (EGP)"),
        _fixed_asset_report_label(t, lang, "net_sale_amount", "Net Sale Amount"),
        _fixed_asset_report_label(t, lang, "deposit_balance", "Deposit Balance"),
        _fixed_asset_report_label(t, lang, "notes", "Notes"),
    ]
    sale_ws.append(sale_headers)
    for cell in sale_ws[1]:
        cell.font = header_font

    for asset in assets:
        asset_data = asset.to_dict()
        sale = asset_data.get("sale")
        if not sale:
            continue
        sale_ws.append(
            [
                asset_data.get("name"),
                sale.get("sale_date"),
                float(sale.get("sale_price") or 0),
                float(sale.get("selling_expenses") or 0),
                float(sale.get("net_sale_amount") or 0),
                sale.get("deposit_balance_id"),
                sale.get("notes"),
            ]
        )

    return sale_ws
