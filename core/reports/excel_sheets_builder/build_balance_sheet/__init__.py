# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
"""build_balance_sheet package.

NOTE: Promoted to its own subfolder under excel_sheets_builder because the
build_balance_sheet function was >200 lines on its own (WealthFlow
refactoring convention: files/functions over 200 lines are split into
packages; a package containing a single over-limit function is further
promoted into its own subfolder).

Phase-function architecture with a BalanceSheetContext dataclass carrier
threaded through each phase:
- context.py    BalanceSheetContext dataclass
- setup.py      column widths, header row, Currency/Bank lookup maps
- home_row.py   home balance row (row 2)
- bank_rows.py  per-bank EGP balance rows (from row 3)
- totals.py     certificate total, EGP total, all-balances total,
                 company pay/work-months totals

This __init__.py is the single umbrella entry point: build_balance_sheet().
"""
from core.reports.excel_sheets_builder.build_balance_sheet.context import (
    BalanceSheetContext,
)
from core.reports.excel_sheets_builder.build_balance_sheet.setup import apply_setup
from core.reports.excel_sheets_builder.build_balance_sheet.home_row import (
    apply_home_row,
)
from core.reports.excel_sheets_builder.build_balance_sheet.bank_rows import (
    apply_bank_rows,
)
from core.reports.excel_sheets_builder.build_balance_sheet.totals import apply_totals

__all__ = ["build_balance_sheet"]


def build_balance_sheet(ws, balance_entries, company_sheet_rows):
    ctx = BalanceSheetContext(
        ws=ws,
        balance_entries=balance_entries,
        company_sheet_rows=company_sheet_rows,
    )
    apply_setup(ctx)
    apply_home_row(ctx)
    apply_bank_rows(ctx)
    apply_totals(ctx)
