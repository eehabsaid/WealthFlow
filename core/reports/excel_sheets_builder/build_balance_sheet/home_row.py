# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
"""NOTE: Part of the excel_sheets_builder/build_balance_sheet subfolder
(promoted because the original build_balance_sheet function was >200 lines
on its own, per WealthFlow refactoring convention). This file holds the
home-balance row phase (row 2: cash/gold held outside any bank).
"""
from core.reports.excel_formatting_helpers import (
    fmt_base_red,
    FMT_USD,
    FMT_EUR,
    FMT_SAR,
    FMT_GOLD,
    fmt_for_code,
    _f,
    _thin,
)
from core.reports.report_context import get_report_base_code


def apply_home_row(ctx):
    ws = ctx.ws
    balance_entries = ctx.balance_entries
    cur_map = ctx.cur_map

    home_cash_entries = [
        be
        for be in balance_entries
        if be.bank_id is None and str(be.balance_type).strip().lower() == "cash"
    ]
    gold_entries = [
        be for be in balance_entries if str(be.balance_type).strip().lower() == "gold"
    ]

    home = {cur_map.get(be.currency_id, "?"): float(be.amount) for be in home_cash_entries}
    if gold_entries:
        home["Gold"] = float(gold_entries[0].amount)

    home_title = home_cash_entries[0].title if home_cash_entries else "Home Balance"
    ws.cell(row=2, column=1, value=home_title).font = _f(bold=True, name="Arial")
    ws.cell(row=2, column=1).border = _thin()

    b2 = ws.cell(row=2, column=2, value=home.get(get_report_base_code(), 0))
    b2.font = _f(bold=True, name="Arial")
    b2.border = _thin()
    b2.number_format = fmt_base_red()

    fixed_formats = {"USD": FMT_USD, "EUR": FMT_EUR, "SAR": FMT_SAR}
    for column, code in zip((3, 4, 5), ctx.slots):
        cell = ws.cell(row=2, column=column, value=home.get(code, 0))
        cell.font = _f(bold=True, name="Arial")
        cell.border = _thin()
        cell.number_format = fixed_formats.get(code) or fmt_for_code(code)

    f2 = ws.cell(row=2, column=6, value=home.get("Gold", 0))
    f2.font = _f(bold=True, name="Arial")
    f2.border = _thin()
    f2.number_format = FMT_GOLD
