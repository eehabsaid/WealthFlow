"""
Phase 4: Excel Workbook export download verification
(/api/export/excel/ -> Balance_Tracker_*.xlsx).
Phase 5: Downstream verification.

Split out of the former monolithic tests/modules/salary.py (200-line rule).
"""

from tests.core.download_verifier import verify_downloaded_file
from tests.core.assertions import verify_downstream_impact


def test_export_and_downstream(context, reporter, screenshot_logger):
    try:
        context.goto_route("#employment")
        context.page.evaluate("if (typeof switchTab === 'function') switchTab('dashboard');")
        context.page.wait_for_timeout(600)

        with context.page.expect_download(timeout=4000) as download_info:
            context.page.evaluate("window.location.href='/api/export/excel/'")
        download = download_info.value
        save_path = f"test_downloads/{download.suggested_filename}"
        download.save_as(save_path)

        verify_downloaded_file(save_path, expected_extension=".xlsx")
        shot_excel = screenshot_logger.capture(context.page, "salary", "dashboard", "none", "excel_download", "ok")
        reporter.exports_tested.append("Salary Dashboard -> Download Excel Workbook")
        reporter.add_step("Salary Dashboard Excel Download", "Employment & Salary", "PASS", f"Verified excel file download: {save_path}", screenshot_path=shot_excel)
    except Exception as ex:
        reporter.add_step("Salary Dashboard Excel Download", "Employment & Salary", "FAIL", f"Exception: {ex}")

    verify_downstream_impact(context.page, "Salary Module Update", "reports")
