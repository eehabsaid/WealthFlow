"""
Phase 3: Expense Record CRUD (showExpenseModal) — real, API-verified.

Split out of the former monolithic tests/modules/expenses.py (200-line rule).
"""

from tests.core.crud_verifier import CrudVerifier


def test_records(context, reporter, screenshot_logger, cat_data):
    exp_checker = CrudVerifier(context.page, api_list_url="/api/expenses/", list_key="entries")
    try:
        context.page.evaluate("if (typeof switchTab === 'function') switchTab('expenses-list');")
        context.page.wait_for_timeout(500)

        before_ids = exp_checker.snapshot_ids()

        context.page.evaluate("if (typeof showExpenseModal === 'function') showExpenseModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Expense Modal")
        shot_exp = screenshot_logger.capture(context.page, "expenses", "exp_modal", "showExpenseModal", "open", "ok")
        exp_checker.add_manual_step(context.page.query_selector("#eAmount") is not None)

        test_amount = 25
        test_desc = f"E2E Test Expense {cat_data['name'][-6:]}"
        if context.page.query_selector("#eAmount"):
            context.page.fill("#eAmount", str(test_amount))
            context.page.fill("#eDesc", test_desc)
            if context.page.query_selector("#eCat"):
                context.page.select_option("#eCat", index=1)
            context.page.evaluate("(async () => { if (typeof saveExpense === 'function') { await saveExpense(); } })()")
            context.page.wait_for_timeout(900)

        create_result = exp_checker.verify_created(before_ids, match_field="description", expected_value=test_desc)

        new_desc = test_desc + " Edited"
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showExpenseModal === 'function') showExpenseModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#eDesc"):
                context.page.fill("#eDesc", new_desc)
                context.page.evaluate(f"(async () => {{ if (typeof saveExpense === 'function') {{ await saveExpense({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(900)
        edit_result = exp_checker.verify_field_updated(create_result.new_id, "description", new_desc)

        if create_result.new_id is not None:
            context.page.evaluate(f"(async () => {{ if (typeof deleteExpense === 'function') {{ await deleteExpense({create_result.new_id}); }} }})()")
            context.page.wait_for_timeout(900)
        delete_result = exp_checker.verify_deleted(create_result.new_id)

        overall_pass = create_result.passed and edit_result.passed and delete_result.passed
        reporter.record_crud("Expense Record", exp_checker.steps_passed, exp_checker.steps_total)
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
        reporter.add_step("Expense Record CRUD (API-verified)", "Expenses & Reports", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot_exp)
    except Exception as ex:
        reporter.record_crud("Expense Record", exp_checker.steps_passed, max(exp_checker.steps_total, 1))
        reporter.add_step("Expense Entry Modal Test", "Expenses & Reports", "FAIL", f"Exception: {ex}")
