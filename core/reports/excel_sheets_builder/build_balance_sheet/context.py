# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
"""NOTE: Part of the excel_sheets_builder/build_balance_sheet subfolder
(promoted because the original build_balance_sheet function was >200 lines
on its own, per WealthFlow refactoring convention). This file holds the
BalanceSheetContext dataclass shared across the build phases.
"""
from dataclasses import dataclass, field

# Fixed currency columns C, D, E of the BALANCE sheet (F is Gold).
DEFAULT_SLOT_CODES = ("USD", "EUR", "SAR")
_GULF_SUBSTITUTES = ("AED", "GBP", "EUR")
_OTHER_SUBSTITUTES = ("EGP", "AED", "GBP")


def resolve_slot_codes(base_code, gulf=False):
    """Codes for columns C/D/E. The base currency already has column B, so a
    default slot equal to the base is replaced by another currency (otherwise
    the base amount would appear twice and be counted twice in the total)."""
    base = str(base_code or "").strip().upper()
    slots = list(DEFAULT_SLOT_CODES)
    for i, code in enumerate(slots):
        if code != base:
            continue
        for candidate in (_GULF_SUBSTITUTES if gulf else _OTHER_SUBSTITUTES):
            if candidate != base and candidate not in slots:
                slots[i] = candidate
                break
    return tuple(slots)


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
    owner: object = None
    slots: tuple = DEFAULT_SLOT_CODES
