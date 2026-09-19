"""
Phase 2: Expense Subcategory CRUD (showSubcategoryModal) — real,
API-verified, plus cleanup of the test category created in phase 1.

Split out of the former monolithic tests/modules/expenses.py (200-line rule).

No flat list endpoint exists for subcategories (only nested inside the
category list), so this uses a small custom before/after check rather
than the generic CrudVerifier. showSubcategoryModal(catId) requires a
real category id — the old test called it with none, which made it
return immediately without rendering anything.
"""


def test_subcategories(context, reporter, screenshot_logger, cat_data, category_id_for_subtest):
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
