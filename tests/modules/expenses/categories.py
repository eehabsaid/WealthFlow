"""
Phase 1: Expense Category CRUD (showCategoryModal) — real, API-verified.

Split out of the former monolithic tests/modules/expenses.py (200-line rule).
"""

from tests.core.crud_verifier import CrudVerifier


def test_categories(context, reporter, screenshot_logger, cat_data):
    cat_checker = CrudVerifier(context.page, api_list_url="/api/expense-categories/", list_key="categories")
    category_id_for_subtest = None
    try:
        before_ids = cat_checker.snapshot_ids()

        context.page.evaluate("if (typeof showCategoryModal === 'function') showCategoryModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Expense Category Modal")
        shot1 = screenshot_logger.capture(context.page, "expenses", "modal_open", "showCategoryModal", "open", "ok")
        cat_checker.add_manual_step(context.page.query_selector("#catName") is not None)

        if context.page.query_selector("#catName"):
            context.page.fill("#catName", cat_data["name"])
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(700)

        create_result = cat_checker.verify_created(before_ids, match_field="name", expected_value=cat_data["name"])

        new_cat_name = cat_data["name"] + " Edited"
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showCategoryModal === 'function') showCategoryModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#catName"):
                context.page.fill("#catName", new_cat_name)
                context.page.evaluate(f"(async () => {{ if (typeof saveCategory === 'function') {{ await saveCategory({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(700)
        edit_result = cat_checker.verify_field_updated(create_result.new_id, "name", new_cat_name)

        category_id_for_subtest = create_result.new_id  # kept for the subcategory test below, deleted after

        overall_pass = create_result.passed and edit_result.passed
        reporter.record_crud("Expense Category", cat_checker.steps_passed, cat_checker.steps_total)
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail}"
        reporter.add_step("Expense Category CRUD (API-verified)", "Expenses & Reports", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot1)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "expenses", "modal", "error", "fail", "fail")
        category_id_for_subtest = None
        reporter.record_crud("Expense Category", cat_checker.steps_passed, max(cat_checker.steps_total, 1))
        reporter.add_step("Expense Category CRUD Test", "Expenses & Reports", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)

    return category_id_for_subtest
