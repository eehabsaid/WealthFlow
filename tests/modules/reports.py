"""
WealthFlow QA Module — Advanced Reports
Tests:
 1. Sweeping sub-tabs (Monthly Analysis, Yearly Analysis, Salary, Balance, Certificates).
 2. Monthly PDF Report generation (generatePDF('monthly') -> report_YYYY_MM.pdf).
 3. Yearly PDF Report generation (generatePDF('yearly') -> report_YYYY.pdf).
"""

from tests.core.download_verifier import verify_downloaded_file

def test_reports_module(context, reporter, screenshot_logger):
    context.goto_route("#reports")
    reporter.pages_visited.add("Advanced Reports")

    # Sweep tabs
    tabs = ["monthly", "yearly", "salary-analytics", "balance-analytics", "certificates-analytics"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchTab === 'function') switchTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Reports -> {t}")

    # Monthly PDF
    try:
        with context.page.expect_download(timeout=4000) as download_info:
            context.page.evaluate("if (typeof generatePDF === 'function') generatePDF('monthly');")
        download = download_info.value
        save_path = f"test_downloads/{download.suggested_filename}"
        download.save_as(save_path)

        verify_downloaded_file(save_path, expected_extension=".pdf")
        shot_m = screenshot_logger.capture(context.page, "reports", "monthly", "none", "pdf_monthly", "ok")
        reporter.exports_tested.append("Advanced Reports -> Generate Monthly PDF")
        reporter.add_step("Monthly PDF Report Download", "Advanced Reports", "PASS", f"Verified PDF file: {save_path}", screenshot_path=shot_m)
    except Exception as ex:
        reporter.add_step("Monthly PDF Report Download", "Advanced Reports", "FAIL", f"Exception: {ex}")

    # Yearly PDF
    try:
        with context.page.expect_download(timeout=4000) as download_info:
            context.page.evaluate("if (typeof generatePDF === 'function') generatePDF('yearly');")
        download = download_info.value
        save_path = f"test_downloads/{download.suggested_filename}"
        download.save_as(save_path)

        verify_downloaded_file(save_path, expected_extension=".pdf")
        shot_y = screenshot_logger.capture(context.page, "reports", "yearly", "none", "pdf_yearly", "ok")
        reporter.exports_tested.append("Advanced Reports -> Generate Yearly PDF")
        reporter.add_step("Yearly PDF Report Download", "Advanced Reports", "PASS", f"Verified PDF file: {save_path}", screenshot_path=shot_y)
    except Exception as ex:
        reporter.add_step("Yearly PDF Report Download", "Advanced Reports", "FAIL", f"Exception: {ex}")
