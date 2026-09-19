"""
Phase 4: CSV Export verification (exportExpenses() -> expenses_*.csv).
Phase 5: Downstream impact verification across affected modules.

Split out of the former monolithic tests/modules/expenses.py (200-line rule).
"""

from tests.core.download_verifier import verify_downloaded_file
from tests.core.assertions import verify_downstream_impact


def test_export_and_downstream(context, reporter, screenshot_logger):
    try:
        with context.page.expect_download(timeout=4000) as download_info:
            context.page.evaluate("if (typeof exportExpenses === 'function') exportExpenses();")
        download = download_info.value
        save_path = f"test_downloads/{download.suggested_filename}"
        download.save_as(save_path)

        verify_downloaded_file(save_path, expected_extension=".csv")
        shot_csv = screenshot_logger.capture(context.page, "expenses", "list", "none", "csv_export", "ok")
        reporter.exports_tested.append("Expenses List -> Export CSV File")
        reporter.add_step("Expenses CSV Download Verification", "Expenses & Reports", "PASS", f"Verified CSV file: {save_path}", screenshot_path=shot_csv)
    except Exception as ex:
        reporter.add_step("Expenses CSV Download", "Expenses & Reports", "FAIL", f"Exception: {ex}")

    verify_downstream_impact(context.page, "Expense Record Creation", "dashboard")
    verify_downstream_impact(context.page, "Expense Record Creation", "financial-advisor")
