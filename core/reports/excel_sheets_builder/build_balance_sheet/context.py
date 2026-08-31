# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
"""NOTE: Part of the excel_sheets_builder/build_balance_sheet subfolder
(promoted because the original build_balance_sheet function was >200 lines
on its own, per WealthFlow refactoring convention). This file holds the
BalanceSheetContext dataclass shared across the build phases.
"""
from dataclasses import dataclass, field


@dataclass
class BalanceSheetContext:
    """Mutable carrier threaded through the balance-sheet build phases.

    `excel_row` acts as a cursor that phases advance as they write rows,
    so later phases know where to continue writing.
    """

    ws: object
    balance_entries: list
    company_sheet_rows: dict
    cur_map: dict = field(default_factory=dict)
    bank_map: dict = field(default_factory=dict)
    excel_row: int = 3
