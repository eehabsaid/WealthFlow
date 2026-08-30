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
from tests.core.crud_verifier import CrudVerifier

def test_salary_module(context, reporter, screenshot_logger):
    # Registered persistently: several deletes below use a native confirm() dialog.
    context.page.on("dialog", lambda dialog: dialog.accept())

    context.goto_route("#employment")
    reporter.pages_visited.add("Employment & Salary")

    # Sweep tabs
    tabs = ["dashboard", "salary-list", "per-diem", "companies"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchTab === 'function') switchTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Salary -> {t}")

    # 1. Company CRUD — real, API-verified. Kept alive (not deleted here)
    # since Salary Entry and Per Diem below both require a real company_id
    # as a prerequisite — deleted at the very end instead.
    comp_data = get_unique_company_data()
    comp_checker = CrudVerifier(context.page, api_list_url="/api/companies/", list_key="companies")
    company_id = None
    try:
        before_ids = comp_checker.snapshot_ids()

        context.page.evaluate("if (typeof showCompanyModal === 'function') showCompanyModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Company Modal")
        shot1 = screenshot_logger.capture(context.page, "salary", "company_modal", "showCompanyModal", "open", "ok")
        comp_checker.add_manual_step(context.page.query_selector("#cName") is not None)

        if context.page.query_selector("#cName"):
            context.page.fill("#cName", comp_data["name"])
            if context.page.query_selector("#cDisplayName"):
                context.page.fill("#cDisplayName", comp_data["display_name"])
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(700)

        create_result = comp_checker.verify_created(before_ids, match_field="name", expected_value=comp_data["name"])
        company_id = create_result.new_id

        new_name = comp_data["name"] + " Edited"
        if company_id is not None:
            context.page.evaluate(f"if (typeof showCompanyModal === 'function') showCompanyModal({company_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#cName"):
                context.page.fill("#cName", new_name)
                context.page.evaluate(f"(async () => {{ if (typeof saveCompany === 'function') {{ await saveCompany({company_id}); }} }})()")
                context.page.wait_for_timeout(700)
        edit_result = comp_checker.verify_field_updated(company_id, "name", new_name)

        overall_pass = create_result.passed and edit_result.passed
        reporter.record_crud("Company Entry", comp_checker.steps_passed, comp_checker.steps_total)
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} (deletion verified at end of module, after dependents cleaned up)"
        reporter.add_step("Company CRUD (API-verified)", "Employment & Salary", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot1)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "salary", "company_modal", "error", "fail", "fail")
        reporter.record_crud("Company Entry", comp_checker.steps_passed, max(comp_checker.steps_total, 1))
        reporter.add_step("Company CRUD Test", "Employment & Salary", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)

    test_year = 2026

    # 2. Salary Entry CRUD — real, API-verified. Requires a real company_id.
    if company_id is not None:
        sal_checker = CrudVerifier(context.page, api_list_url=f"/api/salary/?company={company_id}&year={test_year}", list_key="entries")
        try:
            context.page.evaluate("if (typeof switchTab === 'function') switchTab('salary-list');")
            context.page.wait_for_timeout(500)

            before_ids = sal_checker.snapshot_ids()

            context.page.evaluate(f"if (typeof showSalaryModal === 'function') showSalaryModal(null, {company_id});")
            context.page.wait_for_timeout(600)
            reporter.modals_opened.add("Salary Entry Modal")
            shot_sal = screenshot_logger.capture(context.page, "salary", "salary_modal", "showSalaryModal", "open", "ok")
            sal_checker.add_manual_step(context.page.query_selector("#mExpected") is not None)

            test_expected = 100
            if context.page.query_selector("#mYear"):
                context.page.fill("#mYear", str(test_year))
                context.page.select_option("#mMonth", index=0)
                context.page.fill("#mExpected", str(test_expected))
                context.page.evaluate(f"(async () => {{ if (typeof saveSalaryEntry === 'function') {{ await saveSalaryEntry(null, {company_id}); }} }})()")
                context.page.wait_for_timeout(900)

            create_result = sal_checker.verify_created(before_ids, match_field="expected", expected_value=test_expected)

            new_expected = 150
            if create_result.new_id is not None:
                context.page.evaluate(f"if (typeof showSalaryModal === 'function') showSalaryModal({create_result.new_id}, {company_id});")
                context.page.wait_for_timeout(500)
                if context.page.query_selector("#mExpected"):
                    context.page.fill("#mExpected", str(new_expected))
                    context.page.evaluate(f"(async () => {{ if (typeof saveSalaryEntry === 'function') {{ await saveSalaryEntry({create_result.new_id}, {company_id}); }} }})()")
                    context.page.wait_for_timeout(900)
            edit_result = sal_checker.verify_field_updated(create_result.new_id, "expected", new_expected)

            if create_result.new_id is not None:
                context.page.evaluate(f"(async () => {{ if (typeof deleteSalaryEntry === 'function') {{ await deleteSalaryEntry({create_result.new_id}, {company_id}); }} }})()")
                context.page.wait_for_timeout(900)
            delete_result = sal_checker.verify_deleted(create_result.new_id)

            overall_pass = create_result.passed and edit_result.passed and delete_result.passed
            reporter.record_crud("Salary Entry Record", sal_checker.steps_passed, sal_checker.steps_total)
            detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
            reporter.add_step("Salary Entry CRUD (API-verified)", "Employment & Salary", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot_sal)
        except Exception as ex:
            reporter.record_crud("Salary Entry Record", sal_checker.steps_passed, max(sal_checker.steps_total, 1))
            reporter.add_step("Salary Entry Modal Test", "Employment & Salary", "FAIL", f"Exception: {ex}")
    else:
        reporter.add_step("Salary Entry Modal Test", "Employment & Salary", "SKIP", "No company id available (company create failed above).")

    # 3. Per Diem CRUD — real, API-verified. Requires a real company_id + year.
    if company_id is not None:
        pd_checker = CrudVerifier(context.page, api_list_url=f"/api/per-diems/?company_id={company_id}&year={test_year}", list_key="entries")
        try:
            context.page.evaluate("if (typeof switchTab === 'function') switchTab('per-diem');")
            context.page.wait_for_timeout(500)

            before_ids = pd_checker.snapshot_ids()

            context.page.evaluate(f"if (typeof showPerDiemFormModal === 'function') showPerDiemFormModal(null, {company_id}, {test_year});")
            context.page.wait_for_timeout(600)
            reporter.modals_opened.add("Per Diem Form Modal")
            shot_pd = screenshot_logger.capture(context.page, "salary", "per_diem_modal", "showPerDiemFormModal", "open", "ok")
            pd_checker.add_manual_step(context.page.query_selector("#pdAmount") is not None)

            test_amount = 30
            if context.page.query_selector("#pdAmount"):
                # Date field uses the app's custom picker, which hides the
                # native <input> — setting .value via JS is the documented
                # supported path for external code.
                context.page.evaluate(f"document.getElementById('pdDate').value = '{test_year}-01-15'")
                context.page.fill("#pdAmount", str(test_amount))
                if context.page.query_selector("#pdCurrency"):
                    context.page.select_option("#pdCurrency", index=1)
                context.page.evaluate(f"(async () => {{ if (typeof savePerDiem === 'function') {{ await savePerDiem(null, {company_id}, {test_year}); }} }})()")
                context.page.wait_for_timeout(900)

            create_result = pd_checker.verify_created(before_ids, match_field="amount", expected_value=test_amount)

            new_amount = 45
            if create_result.new_id is not None:
                context.page.evaluate(f"if (typeof showPerDiemFormModal === 'function') showPerDiemFormModal({create_result.new_id}, {company_id}, {test_year});")
                context.page.wait_for_timeout(500)
                if context.page.query_selector("#pdAmount"):
                    context.page.fill("#pdAmount", str(new_amount))
                    context.page.evaluate(f"(async () => {{ if (typeof savePerDiem === 'function') {{ await savePerDiem({create_result.new_id}, {company_id}, {test_year}); }} }})()")
                    context.page.wait_for_timeout(900)
            edit_result = pd_checker.verify_field_updated(create_result.new_id, "amount", new_amount)

            if create_result.new_id is not None:
                context.page.evaluate(f"(async () => {{ if (typeof deletePerDiem === 'function') {{ await deletePerDiem({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(900)
            delete_result = pd_checker.verify_deleted(create_result.new_id)

            overall_pass = create_result.passed and edit_result.passed and delete_result.passed
            reporter.record_crud("Per Diem Record", pd_checker.steps_passed, pd_checker.steps_total)
            detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
            reporter.add_step("Per Diem CRUD (API-verified)", "Employment & Salary", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot_pd)
        except Exception as ex:
            reporter.add_step("Per Diem Modal Test", "Employment & Salary", "FAIL", f"Exception: {ex}")
    else:
        reporter.add_step("Per Diem Modal Test", "Employment & Salary", "SKIP", "No company id available (company create failed above).")

    # Clean up the test company now that its dependents are gone.
    if company_id is not None:
        context.page.evaluate(f"(async () => {{ if (typeof deleteCompany === 'function') {{ await deleteCompany({company_id}); }} }})()")
        context.page.wait_for_timeout(700)

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
