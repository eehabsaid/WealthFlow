# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
"""NOTE: Part of the excel_sheets_builder/build_balance_sheet subfolder
(promoted because the original build_balance_sheet function was >200 lines
on its own, per WealthFlow refactoring convention). This file holds the
per-bank EGP balance rows phase (starting at row 3), advancing ctx.excel_row.
"""
from core.reports.excel_formatting_helpers import FMT_EGP_RED, FMT_INT, _f, _thin


def apply_bank_rows(ctx):
    ws = ctx.ws
    cur_map = ctx.cur_map
    bank_map = ctx.bank_map

    excel_row = 3
    for be in sorted(ctx.balance_entries, key=lambda b: b.id):
        if be.bank_id is None or str(be.balance_type).strip().lower() in (
            "certificate",
            "gold",
        ):
            continue
        if cur_map.get(be.currency_id) != "EGP":
            continue

        a = ws.cell(row=excel_row, column=1, value=be.title)
        a.font = _f(bold=True, name="Arial")
        a.border = _thin()
        b = ws.cell(row=excel_row, column=2, value=float(be.amount))
        b.font = _f(bold=True, name="Arial")
        b.border = _thin()
        b.number_format = FMT_EGP_RED

        bank = bank_map.get(be.bank_id)
        if bank:
            for col, attr in [
                (7, "account_number"),
                (8, "card_number"),
                (9, "swift_code"),
                (10, "customer_id"),
                (11, "customer_name"),
            ]:
                v = getattr(bank, attr, "") or ""
                cell = ws.cell(row=excel_row, column=col, value=v)
                cell.font = _f(bold=True, name="Arial")
                cell.border = _thin()
                if col in (7, 8):
                    cell.number_format = FMT_INT
        excel_row += 1

    ctx.excel_row = excel_row
