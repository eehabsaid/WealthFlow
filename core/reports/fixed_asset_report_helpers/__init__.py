# pyright: reportMissingTypeStubs=false
"""
Fixed-asset report helpers: queryset/context building, value
formatting, and PDF table/story construction.

Split into a package (200-line rule):
  - context.py   : queryset, context, display_value, label, user_text
  - pdf_story.py : pdf_table, build_fixed_asset_pdf_story
  - __init__.py (this file) : umbrella re-export, preserving the exact
    import surface consumers already depend on (report_generators.py,
    fixed_asset_pdf_report_generator.py, fixed_asset_excel_report_generator/*.py)
"""

from core.reports.fixed_asset_report_helpers.context import (
    fixed_asset_report_queryset,
    fixed_asset_report_context,
    fixed_asset_display_value,
    fixed_asset_report_label,
    fixed_asset_user_text,
)
from core.reports.fixed_asset_report_helpers.pdf_story import (
    fixed_asset_pdf_table,
    build_fixed_asset_pdf_story,
)

__all__ = [
    "fixed_asset_report_queryset",
    "fixed_asset_report_context",
    "fixed_asset_display_value",
    "fixed_asset_report_label",
    "fixed_asset_user_text",
    "fixed_asset_pdf_table",
    "build_fixed_asset_pdf_story",
]
