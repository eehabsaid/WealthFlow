"""
Phase 2: Salary Entry CRUD (showSalaryModal) — real, API-verified.
Requires a real company_id.

Split out of the former monolithic tests/modules/salary.py (200-line rule).
"""

from tests.core.crud_verifier import CrudVerifier


def test_salary_entry(context, reporter, screenshot_logger, company_id, test_year):
    if company_id is None:
        reporter.add_step("Salary Entry Modal Test", "Employment & Salary", "SKIP", "No company id available (company create failed above).")
        return

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
            # #mMonth options are the 12 fixed literal month names (not
            # dynamic per-install data), so selecting by value is exact
            # and stable - unlike select_option(index=0), which has been
            # observed to clear the select's value entirely on some
            # Playwright/browser combinations.
            context.page.select_option("#mMonth", value="January")
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
