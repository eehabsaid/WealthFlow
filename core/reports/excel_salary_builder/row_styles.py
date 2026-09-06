"""Per-cell row styling helpers for the salary Excel sheet builder.

Pure code motion from the original excel_salary_builder.py — same logic,
only relocated for file-size compliance.
"""

from openpyxl.styles import Font

from core.reports.excel_formatting_helpers import FMT_EGP, _thin, _center


def _apply_data_row(ws, row, has_bonus=False):
    cols = 6 if has_bonus else 5
    for c in range(1, cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(name="Arial")
        cell.border = _thin()
        if c in (3, 4, 5):
            cell.number_format = FMT_EGP
        if has_bonus and c == 6:
            cell.number_format = FMT_EGP


def _apply_total_row(ws, row, has_bonus=False):
    cols = 6 if has_bonus else 5
    for c in range(1, cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(bold=True, name="Arial")
        cell.border = _thin()
        cell.alignment = _center()
        if c in (3, 4):
            cell.number_format = FMT_EGP
        if c == 5:
            cell.number_format = FMT_EGP
        if has_bonus and c == 6:
            cell.number_format = FMT_EGP
