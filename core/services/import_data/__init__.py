"""CSV/Excel/bank-statement import (A3): no live bank sync (unrealistic
for Egypt/Gulf retail banking) — the user exports a statement and
uploads it here instead.

Sibling files:
- parsers.py: file -> (headers, rows), CSV and XLSX.
- column_mapper.py: header-name heuristics + date/amount value parsing.
- duplicate_detector.py: flags rows that already exist as an Expense.
- import_service.py: ImportService.preview()/confirm() orchestration,
  the two calls the views use.
"""
from .import_service import ImportService

__all__ = ["ImportService"]
