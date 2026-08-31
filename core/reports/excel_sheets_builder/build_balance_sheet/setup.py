# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
"""NOTE: Part of the excel_sheets_builder/build_balance_sheet subfolder
(promoted because the original build_balance_sheet function was >200 lines
on its own, per WealthFlow refactoring convention). This file holds the
setup phase: column widths, header row, and Currency/Bank lookup maps.
"""
from core.reports.excel_formatting_helpers import _f, _thin, _thin_lr


def apply_setup(ctx):
    ws = ctx.ws

    ws.column_dimensions["A"].width = 26.5
    ws.column_dimensions["B"].width = 14.6
    ws.column_dimensions["C"].width = 12.5
    ws.column_dimensions["D"].width = 13.1
    ws.column_dimensions["E"].width = 13.1
    ws.column_dimensions["F"].width = 14.4
    ws.column_dimensions["G"].width = 14.4
    ws.column_dimensions["H"].width = 17.1
    ws.column_dimensions["I"].width = 12.7
    ws.column_dimensions["J"].width = 12.0
    ws.column_dimensions["K"].width = 29.7
    ws.row_dimensions[7].height = 18.0

    hdrs = [
        "Title",
        "EGP",
        "USD",
        "EUR",
        "SAR",
        "Gold",
        "Acct-Number",
        "Card-ID",
        "Swift-Code",
        "Customer-id",
        "Customer-Name",
    ]
    border_map = {
        1: _thin(),
        2: _thin(),
        3: _thin(),
        4: _thin_lr(),
        5: _thin_lr(),
        6: _thin_lr(),
        7: _thin_lr(),
        8: _thin_lr(),
        9: _thin(),
        10: _thin(),
        11: _thin(),
    }
    for c, h in enumerate(hdrs, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = _f(bold=True, name="Arial")
        cell.border = border_map.get(c, _thin())

    from core.models import Currency, Bank as BankModel

    ctx.cur_map = {c.id: c.code for c in Currency.objects.all()}
    ctx.bank_map = {b.id: b for b in BankModel.objects.all()}
