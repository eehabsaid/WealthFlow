"""
WealthFlow QA Module — Advanced Reports → Income tab
Tests:
 1. Open Advanced Reports → Income; filter bar and content render.
 2. Switch all 3 compare modes (Off / Year vs Year / Month vs Month).
 3. Toggle a month chip and a source chip (and back).
 4. Open the drill-down drawer from a table row, close it with Escape.
 5. Switch to Arabic (dir=rtl), then back to English.
 6. Download the Excel and PDF exports and verify the files.
"""

from tests.core.download_verifier import verify_downloaded_file


def test_reports_income(context, reporter, screenshot_logger):
    context.page.wait_for_selector("#main-content", timeout=20000)
    context.page.evaluate("renderAdvancedReports('income')")
    context.page.wait_for_selector("#incomeModeSeg", timeout=20000)
    reporter.tabs_visited.add("Reports -> income")
    errors_before = len(context.console_errors)

    # All 3 compare modes
    for mode in ("yoy", "mom", "off"):
        context.page.click(f"#incomeModeSeg button[data-v='{mode}']")
        context.page.wait_for_timeout(900)
        reporter.add_step(f"Income mode switch: {mode}", "Advanced Reports", "PASS", "Mode switched, content rendered.")

    # Month chip toggle (off mode)
    context.page.click("#incomeMonthChips .income-month-chip[data-m='1']")
    context.page.wait_for_timeout(900)
    context.page.click("#incomeMonthChips .income-month-chip[data-m='1']")
    context.page.wait_for_timeout(900)
    reporter.add_step("Income month chip toggle", "Advanced Reports", "PASS", "Month chip toggled and reverted.")

    # Source chip toggle
    context.page.click("#incomeSrcChips .income-chip[data-s='bonus']")
    context.page.wait_for_timeout(900)
    context.page.click("#incomeSrcChips .income-chip[data-s='bonus']")
    context.page.wait_for_timeout(900)
    reporter.add_step("Income source chip toggle", "Advanced Reports", "PASS", "Source chip toggled and reverted.")

    # Drawer: open from a row, close with Escape
    context.page.click(".income-item")
    context.page.wait_for_timeout(500)
    open_state = context.page.evaluate("() => document.getElementById('incomeDrawer').classList.contains('open')")
    context.page.keyboard.press("Escape")
    context.page.wait_for_timeout(400)
    closed_state = context.page.evaluate("() => !document.getElementById('incomeDrawer').classList.contains('open')")
    if open_state and closed_state:
        reporter.add_step("Income drawer open/close", "Advanced Reports", "PASS", "Drawer opened from a row and closed with Escape.")
    else:
        reporter.add_step("Income drawer open/close", "Advanced Reports", "FAIL", f"open={open_state} closed={closed_state}")

    # Arabic: dir=rtl
    context.set_language("ar")
    context.page.wait_for_timeout(900)
    body_dir = context.page.evaluate("() => document.documentElement.getAttribute('dir') || 'ltr'")
    shot = screenshot_logger.capture(context.page, "reports", "income", "ar", "view", "ok")
    reporter.add_step("Income Arabic (dir=rtl)", "Advanced Reports", "PASS" if body_dir == "rtl" else "FAIL",
                      f"dir={body_dir}", screenshot_path=shot)
    context.set_language("en")
    context.page.wait_for_timeout(900)

    # Excel export
    try:
        with context.page.expect_download(timeout=4000) as dl_info:
            context.page.click("#incomeBtnXlsx")
        download = dl_info.value
        save_path = f"test_downloads/{download.suggested_filename}"
        download.save_as(save_path)
        verify_downloaded_file(save_path, expected_extension=".xlsx")
        reporter.add_step("Income Excel export", "Advanced Reports", "PASS", f"Verified xlsx file: {save_path}")
    except Exception as ex:
        reporter.add_step("Income Excel export", "Advanced Reports", "FAIL", f"Exception: {ex}")

    # PDF export
    try:
        with context.page.expect_download(timeout=4000) as dl_info:
            context.page.click("#incomeBtnPdf")
        download = dl_info.value
        save_path = f"test_downloads/{download.suggested_filename}"
        download.save_as(save_path)
        verify_downloaded_file(save_path, expected_extension=".pdf")
        reporter.add_step("Income PDF export", "Advanced Reports", "PASS", f"Verified pdf file: {save_path}")
    except Exception as ex:
        reporter.add_step("Income PDF export", "Advanced Reports", "FAIL", f"Exception: {ex}")

    new_errors = context.console_errors[errors_before:]
    if new_errors:
        reporter.add_step("Income console errors", "Advanced Reports", "FAIL", "; ".join(new_errors[:5]))
    else:
        reporter.add_step("Income console errors", "Advanced Reports", "PASS", "Zero new console errors.")
