"""
fixed_asset_excel_report_generator package
=============================================
Split from the former `fixed_asset_excel_report_generator.py` module
(200-line refactor), using the phase-function pattern: each sheet is built
by an independent phase function, orchestrated by the thin generator class.

Sibling files:
- summary_sheet.py      build_summary_sheet() — the "Summary" worksheet
                        (one row per asset + optional portfolio totals).
- sale_sheet.py          build_sale_sheet() — the "Sale" worksheet.
- collection_sheets.py   get_collection_definitions() + build_collection_sheets()
                        — the per-asset sub-collection worksheets
                        (Acquisition Costs, Renovations, Furniture,
                        Valuations, Photos).
- formatting.py          autofit_columns() + build_xlsx_response() — shared
                        post-processing and the final HttpResponse.
- generator.py           FixedAssetExcelReportGenerator — orchestrates the
                        phases above.

Update this docstring whenever a sibling file is added, removed, or its
responsibility changes.
"""

from __future__ import annotations

from core.reports.fixed_asset_excel_report_generator.generator import FixedAssetExcelReportGenerator

__all__ = ["FixedAssetExcelReportGenerator"]
