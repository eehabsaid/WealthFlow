"""
WealthFlow QA Module — Expenses & Reports
Tests:
 1. 17-step CRUD on Expense Categories (showCategoryModal), Subcategories (showSubcategoryModal), and Expense Records (showExpenseModal).
 2. CSV Export verification (exportExpenses() -> expenses_*.csv).
 3. Immediate downstream verification (Dashboard, Reports, Cash Flow, Spending Intelligence).
"""

from tests.core.data_generator import get_unique_expense_category_data
from tests.core.download_verifier import verify_downloaded_file
from tests.core.assertions import verify_downstream_impact
from tests.core.crud_verifier import CrudVerifier

def test_expenses_module(context, reporter, screenshot_logger):
    # Registered persistently: delete uses a native confirm() dialog.
    context.page.on("dialog", lambda dialog: dialog.accept())

    context.goto_route("#expenses")
    reporter.pages_visited.add("Expenses & Reports")

    # Sweep tabs
    tabs = ["expenses-list", "expense-categories", "expense-subcategories", "reports-summary"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchTab === 'function') switchTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Expenses -> {t}")

    # 1. Expense Category CRUD — real, API-verified
    cat_data = get_unique_expense_category_data()
    cat_checker = CrudVerifier(context.page, api_list_url="/api/expense-categories/", list_key="categories")
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

    # 2. Expense Subcategory CRUD — real, API-verified.
    # No flat list endpoint exists for subcategories (only nested inside
    # the category list), so this uses a small custom before/after check
    # rather than the generic CrudVerifier. showSubcategoryModal(catId)
    # requires a real category id — the old test called it with none,
    # which made it return immediately without rendering anything.
    sub_steps_passed = 0
    sub_steps_total = 0
    try:
        context.page.evaluate("if (typeof switchTab === 'function') switchTab('expense-subcategories');")
        context.page.wait_for_timeout(500)

        if category_id_for_subtest is not None:
            context.page.evaluate(f"if (typeof showSubcategoryModal === 'function') showSubcategoryModal({category_id_for_subtest});")
            context.page.wait_for_timeout(600)
            reporter.modals_opened.add("Expense Subcategory Modal")
            shot_sub = screenshot_logger.capture(context.page, "expenses", "subcat_modal", "showSubcategoryModal", "open", "ok")
            sub_steps_total += 1
            has_input = context.page.query_selector("#newSubName") is not None
            if has_input:
                sub_steps_passed += 1

            sub_name = "Test Sub " + cat_data["name"][-6:]
            if has_input:
                context.page.fill("#newSubName", sub_name)
                context.page.evaluate(f"(async () => {{ if (typeof addSubcategory === 'function') {{ await addSubcategory({category_id_for_subtest}); }} }})()")
                context.page.wait_for_timeout(700)

            after = context.page.evaluate("""async (catId) => {
                const r = await fetch('/api/expense-categories/');
                const data = await r.json();
                const cat = (data.categories || []).find(c => c.id === catId);
                return cat ? cat.subcategories : [];
            }""", category_id_for_subtest)
            created_sub = next((s for s in after if s.get("name") == sub_name), None)
            sub_steps_total += 1
            if created_sub:
                sub_steps_passed += 1
                sub_id = created_sub["id"]

                # Edit via the real per-row save (fills the row's own input, calls saveSubcategory(id))
                context.page.evaluate(f"if (typeof showSubcategoryModal === 'function') showSubcategoryModal({category_id_for_subtest});")
                context.page.wait_for_timeout(500)
                new_sub_name = sub_name + " Edited"
                if context.page.query_selector(f"#sub_{sub_id}"):
                    context.page.fill(f"#sub_{sub_id}", new_sub_name)
                    context.page.evaluate(f"(async () => {{ if (typeof saveSubcategory === 'function') {{ await saveSubcategory({sub_id}); }} }})()")
                    context.page.wait_for_timeout(700)
                after_edit = context.page.evaluate("""async (catId) => {
                    const r = await fetch('/api/expense-categories/');
                    const data = await r.json();
                    const cat = (data.categories || []).find(c => c.id === catId);
                    return cat ? cat.subcategories : [];
                }""", category_id_for_subtest)
                sub_steps_total += 1
                if any(s.get("id") == sub_id and s.get("name") == new_sub_name for s in after_edit):
                    sub_steps_passed += 1

                context.page.evaluate(f"(async () => {{ if (typeof deleteSubcategory === 'function') {{ await deleteSubcategory({sub_id}, {category_id_for_subtest}); }} }})()")
                context.page.wait_for_timeout(700)
                after_delete = context.page.evaluate("""async (catId) => {
                    const r = await fetch('/api/expense-categories/');
                    const data = await r.json();
                    const cat = (data.categories || []).find(c => c.id === catId);
                    return cat ? cat.subcategories : [];
                }""", category_id_for_subtest)
                sub_steps_total += 1
                if not any(s.get("id") == sub_id for s in after_delete):
                    sub_steps_passed += 1

            reporter.record_crud("Expense Subcategory", sub_steps_passed, sub_steps_total)
            reporter.add_step(
                "Expense Subcategory CRUD (API-verified)", "Expenses & Reports",
                "PASS" if sub_steps_passed == sub_steps_total else "FAIL",
                f"{sub_steps_passed}/{sub_steps_total} sub-steps verified via /api/expense-categories/ nested data.",
                screenshot_path=shot_sub,
            )
        else:
            reporter.add_step("Expense Subcategory CRUD Test", "Expenses & Reports", "SKIP", "No category id available (category create failed above).")
    except Exception as ex:
        reporter.record_crud("Expense Subcategory", sub_steps_passed, max(sub_steps_total, 1))
        reporter.add_step("Expense Subcategory Modal Test", "Expenses & Reports", "FAIL", f"Exception: {ex}")

    # Clean up the test category now that the subcategory test is done with it.
    if category_id_for_subtest is not None:
        context.page.evaluate(f"(async () => {{ if (typeof deleteCategory === 'function') {{ await deleteCategory({category_id_for_subtest}); }} }})()")
        context.page.wait_for_timeout(700)

    # 3. Expense Record CRUD — real, API-verified
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

    # 4. CSV Export Test
    try:
        with context.page.expect_download(timeout=4000) as download_info:
            context.page.evaluate("if (typeof exportExpenses === 'function') exportExpenses();")
        download = download_info.value
        save_path = f"test_downloads/{download.suggested_filename}"
        download.save_as(save_path)

        verify_downloaded_file(save_path, expected_extension=".csv")
        shot_csv = screenshot_logger.capture(context.page, "expenses", "list", "none", "csv_export", "ok")
        reporter.exports_tested.append("Expenses List -> Export CSV File")
        reporter.add_step("Expenses CSV Download Verification", "Expenses & Reports", "PASS", f"Verified CSV file: {save_path}", screenshot_path=shot_csv)
    except Exception as ex:
        reporter.add_step("Expenses CSV Download", "Expenses & Reports", "FAIL", f"Exception: {ex}")

    # 5. Downstream impact verification across affected modules
    verify_downstream_impact(context.page, "Expense Record Creation", "dashboard")
    verify_downstream_impact(context.page, "Expense Record Creation", "financial-advisor")
