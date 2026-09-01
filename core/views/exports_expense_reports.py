"""Umbrella re-export for the Expenses & Reporting domain: expense
categories/subcategories, expense entries, expense summaries, and the
Excel/PDF report generation views + their helper functions.

Whenever expense_category_views.py, expense_views.py,
expense_summary_views.py, report_views.py, or
core/reports/report_generators.py grow and add/remove a public name,
update the imports/__all__ below to match — this file is what
core/views/__init__.py depends on, so no other file needs to change
when those are reorganized internally.
"""

from .expense_category_views import (
    ExpenseCategoryListView,
    ExpenseCategoryDetailView,
    ExpenseSubcategoryListView,
    ExpenseSubcategoryDetailView,
)
from .expense_views import ExpenseListView, ExpenseDetailView, User
from .expense_summary_views import ExpenseSummaryView
from .report_views import (
    ExportExcelWorkbookView,
    export_excel,
    GenerateReportView,
    SalaryReportView,
    BalanceReportView,
    CertificateReportView,
    FixedAssetPdfReportView,
    FixedAssetExcelReportView,
)
from core.reports.report_generators import (
    format_arabic,
    get_text,
    _fixed_asset_report_queryset,
    _fixed_asset_report_context,
    _fixed_asset_display_value,
    _fixed_asset_report_label,
    _fixed_asset_user_text,
    _fixed_asset_pdf_table,
    _build_fixed_asset_pdf_story,
    month_sort_key,
)

__all__ = [
    "ExpenseCategoryListView",
    "ExpenseCategoryDetailView",
    "ExpenseSubcategoryListView",
    "ExpenseSubcategoryDetailView",
    "ExpenseListView",
    "ExpenseDetailView",
    "User",
    "ExpenseSummaryView",
    "ExportExcelWorkbookView",
    "export_excel",
    "GenerateReportView",
    "SalaryReportView",
    "BalanceReportView",
    "CertificateReportView",
    "FixedAssetPdfReportView",
    "FixedAssetExcelReportView",
    "format_arabic",
    "get_text",
    "_fixed_asset_report_queryset",
    "_fixed_asset_report_context",
    "_fixed_asset_display_value",
    "_fixed_asset_report_label",
    "_fixed_asset_user_text",
    "_fixed_asset_pdf_table",
    "_build_fixed_asset_pdf_story",
    "month_sort_key",
]
