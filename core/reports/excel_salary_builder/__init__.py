"""
excel_salary_builder  –  Salary Excel sheet builder
=====================================================
Builds the styled "Salary Details" worksheet for one company, replicating
the exact theme RGB values, fonts, and formulas of the original workbook.

Package layout
--------------
Split into a package (was a single >200-line module) per the project's
200-line-per-file convention, mirroring the sibling `excel_sheets_builder/`
package's one-file-per-concern layout.

- constants.py          SALARY_COL_WIDTHS, YEAR_ROW_HT, SALARY_FREEZE
- row_styles.py          _apply_data_row, _apply_total_row (generic cell styling
                         helpers used by callers outside this module)
- frame_and_header.py   sheet frame (row heights/col widths/freeze panes),
                         header row (row 1), title banner (rows 2-3)
- year_group.py          per-year row group: year label row, data rows,
                         per-year total row
- grand_total.py         final grand-total row summing all per-year totals

All symbols previously importable from `excel_salary_builder` (constants,
row-styling helpers, and `build_salary_sheet` itself) are re-exported here.
"""

from itertools import groupby

from core.reports.excel_formatting_helpers import _msort

from .constants import SALARY_COL_WIDTHS, YEAR_ROW_HT, SALARY_FREEZE
from .row_styles import _apply_data_row, _apply_total_row
from .frame_and_header import setup_sheet_frame, build_header_row, build_title_row
from .year_group import build_year_group
from .grand_total import build_grand_total

__all__ = [
    "SALARY_COL_WIDTHS",
    "YEAR_ROW_HT",
    "SALARY_FREEZE",
    "_apply_data_row",
    "_apply_total_row",
    "build_salary_sheet",
]


def build_salary_sheet(ws, company, entries):
    """Exact replica of original salary sheet styling using theme RGB values."""
    name = company.name
    has_bonus = True
    cols = 6
    last_col = "F"

    setup_sheet_frame(ws, name)
    build_header_row(ws, has_bonus)
    build_title_row(ws, last_col, has_bonus)

    row = 4
    total_rows = []
    sorted_entries = sorted(entries, key=lambda e: (e.year, _msort(str(e.month))))

    for year, ygrp in groupby(sorted_entries, key=lambda e: e.year):
        year_entries = list(ygrp)
        row, total_row = build_year_group(
            ws, row, year, year_entries, name, cols, last_col, has_bonus,
            is_first_group=(len(total_rows) == 0),
        )
        total_rows.append(total_row)

    return build_grand_total(ws, row, total_rows, name, cols, has_bonus)
