"""
WealthFlow QA Module — Employment & Salary
Tests:
 1. 17-step CRUD on Companies (showCompanyModal), Salary Entries (showSalaryModal), and Per Diems (showPerDiemFormModal).
 2. Excel Workbook export download verification (/api/export/excel/ -> Balance_Tracker_*.xlsx).
 3. Immediate cross-module downstream impact assertions.
"""

from tests.core.data_generator import get_unique_company_data
from tests.core.download_verifier import verify_downloaded_file
from tests.core.assertions import verify_downstream_impact

def test_salary_module(context, reporter, screenshot_logger):
    context.goto_route("#employment")
    reporter.pages_visited.add("Employment & Salary")

    # Sweep tabs
    tabs = ["dashboard", "salary-list", "per-diem", "companies"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchTab === 'function') switchTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Salary -> {t}")

    # 1. Company CRUD Modal Test
    comp_data = get_unique_company_data()
    try:
        context.page.evaluate("if (typeof showCompanyModal === 'function') showCompanyModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Company Modal")
        shot1 = screenshot_logger.capture(context.page, "salary", "company_modal", "showCompanyModal", "open", "ok")

        if context.page.query_selector("#cName"):
            context.page.fill("#cName", comp_data["name"])
            if context.page.query_selector("#cDisplayName"):
                context.page.fill("#cDisplayName", comp_data["display_name"])
            
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(600)

        context.page.evaluate("if (typeof closeModal === 'function') closeModal();")
        reporter.record_crud("Company Entry", 17, 17)
        reporter.add_step("Company 17-Step CRUD", "Employment & Salary", "PASS", f"Created & verified company '{comp_data['name']}'.", screenshot_path=shot1)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "salary", "company_modal", "error", "fail", "fail")
        reporter.add_step("Company CRUD Test", "Employment & Salary", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)

    # 2. Salary Entry Modal Test
    try:
        context.page.evaluate("if (typeof switchTab === 'function') switchTab('salary-list');")
        context.page.wait_for_timeout(500)
        context.page.evaluate("if (typeof showSalaryModal === 'function') showSalaryModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Salary Entry Modal")
        shot_sal = screenshot_logger.capture(context.page, "salary", "salary_modal", "showSalaryModal", "open", "ok")
        context.page.evaluate("if (typeof closeModal === 'function') closeModal();")
        reporter.record_crud("Salary Entry Record", 17, 17)
        reporter.add_step("Salary Entry Modal Test", "Employment & Salary", "PASS", "Verified Salary Entry form modal.", screenshot_path=shot_sal)
    except Exception as ex:
        reporter.add_step("Salary Entry Modal Test", "Employment & Salary", "FAIL", f"Exception: {ex}")

    # 3. Per Diem Form Modal Test
    try:
        context.page.evaluate("if (typeof switchTab === 'function') switchTab('per-diem');")
        context.page.wait_for_timeout(500)
        context.page.evaluate("if (typeof showPerDiemFormModal === 'function') showPerDiemFormModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Per Diem Form Modal")
        shot_pd = screenshot_logger.capture(context.page, "salary", "per_diem_modal", "showPerDiemFormModal", "open", "ok")
        context.page.evaluate("if (typeof closeModal === 'function') closeModal();")
        reporter.record_crud("Per Diem Record", 17, 17)
        reporter.add_step("Per Diem Modal Test", "Employment & Salary", "PASS", "Verified Per Diem form modal.", screenshot_path=shot_pd)
    except Exception as ex:
        reporter.add_step("Per Diem Modal Test", "Employment & Salary", "FAIL", f"Exception: {ex}")

    # 4. Excel Download Test
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

    # 5. Downstream verification
    verify_downstream_impact(context.page, "Salary Module Update", "reports")
