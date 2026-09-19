"""
Phase 3: Per Diem CRUD (showPerDiemFormModal) — real, API-verified.
Requires a real company_id + year. Also cleans up the test company
created in company.py now that its dependents are gone.

Split out of the former monolithic tests/modules/salary.py (200-line rule).
"""

from tests.core.crud_verifier import CrudVerifier


def test_per_diem(context, reporter, screenshot_logger, company_id, test_year):
    if company_id is None:
        reporter.add_step("Per Diem Modal Test", "Employment & Salary", "SKIP", "No company id available (company create failed above).")
        return

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
                # #pdCurrency's option[0] is the blank "Select Currency"
                # placeholder and the real options are dynamic per-install
                # currency ids, so there's no fixed literal to select by
                # value. Read the first real option's actual value and
                # select by that instead of select_option(index=1), which
                # has been observed to clear the select's value entirely
                # on some Playwright/browser combinations.
                first_currency_value = context.page.eval_on_selector(
                    "#pdCurrency", "el => (el.options[1] || el.options[0])?.value || ''"
                )
                if first_currency_value:
                    context.page.select_option("#pdCurrency", value=first_currency_value)
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

    # Clean up the test company now that its dependents are gone.
    context.page.evaluate(f"(async () => {{ if (typeof deleteCompany === 'function') {{ await deleteCompany({company_id}); }} }})()")
    context.page.wait_for_timeout(700)
