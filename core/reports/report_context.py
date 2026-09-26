# pyright: reportMissingTypeStubs=false
"""Per-report base-currency context.

Report generation (Excel/PDF) happens through many small builder functions
(cell-by-cell, row-by-row) that were never written to receive an `owner` or
`base_code` argument, and there are 100+ call sites across the reports
package. Rather than threading a new parameter through every one of them,
each top-level report entry point (generate_excel, GenerateReportGenerator,
FixedAssetPdfReportGenerator/FixedAssetExcelReportGenerator, ...) calls
set_report_base_code() once, and the formatting/label helpers
(excel_formatting_helpers.py's dynamic formats, report_utils.get_text's
{base} token substitution) read it back via get_report_base_code().

threading.local() rather than a plain module global: Django's dev/prod WSGI
workers can serve more than one request concurrently on the same process,
so a plain global would leak one user's base currency into another's
report if two requests overlapped on the same worker thread. Each request
still runs on a single thread throughout, so thread-local is exactly the
right scope here (same pattern as currency_conversion_service's rate-pivot
handling in A6 batch 4a, applied here for the same "not a bare EGP
default" reason).
"""
import threading

_local = threading.local()

_FALLBACK = "EGP"  # only used if a report entry point forgot to set the context


def set_report_base_code(code) -> None:
    _local.base_code = str(code or _FALLBACK).strip().upper()


def get_report_base_code() -> str:
    return getattr(_local, "base_code", _FALLBACK)
