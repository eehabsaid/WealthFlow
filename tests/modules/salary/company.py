"""
Phase 1: Company CRUD (showCompanyModal) — real, API-verified.

Split out of the former monolithic tests/modules/salary.py (200-line rule).

Kept alive (not deleted here) since Salary Entry and Per Diem below both
require a real company_id as a prerequisite — deleted at the very end
of the module instead (see per_diem.py's cleanup step).
"""

from tests.core.crud_verifier import CrudVerifier


def test_company(context, reporter, screenshot_logger, comp_data):
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

    return company_id
