"""Phase 2: Budget CRUD (showBudgetModal / saveBudget / deleteBudget) — API-verified."""

import time

from tests.core.crud_verifier import CrudVerifier


def test_budget_crud(context, reporter, screenshot_logger):
    page = context.page
    checker = CrudVerifier(page, api_list_url="/api/budgets/", list_key="budgets")
    name = f"E2E Budget {str(int(time.time() * 1000))[-6:]}"
    try:
        context.goto_route("#budgets")
        before_ids = checker.snapshot_ids()

        page.evaluate("if (typeof showBudgetModal === 'function') showBudgetModal(null);")
        page.wait_for_timeout(600)
        reporter.modals_opened.add("Budget Modal")
        shot = screenshot_logger.capture(page, "budgets", "modal", "showBudgetModal", "open", "ok")
        checker.add_manual_step(page.query_selector("#bName") is not None)

        if page.query_selector("#bName"):
            page.fill("#bName", name)
            page.fill("#bAmount", "5000")
            page.evaluate("(async () => { if (typeof saveBudget === 'function') { await saveBudget(null); } })()")
            page.wait_for_timeout(900)
        created = checker.verify_created(before_ids, match_field="name", expected_value=name)

        new_name = name + " Edited"
        if created.new_id is not None:
            page.evaluate(f"if (typeof showBudgetModal === 'function') showBudgetModal({{id: {created.new_id}, name: '{name}', period: 'monthly', amount: 5000, alert_threshold_percent: 80, category_id: null, currency_code: null}});")
            page.wait_for_timeout(500)
            if page.query_selector("#bName"):
                page.fill("#bName", new_name)
                page.evaluate(f"(async () => {{ if (typeof saveBudget === 'function') {{ await saveBudget({created.new_id}); }} }})()")
                page.wait_for_timeout(900)
        edited = checker.verify_field_updated(created.new_id, "name", new_name)

        if created.new_id is not None:
            page.evaluate(f"(async () => {{ if (typeof deleteBudget === 'function') {{ await deleteBudget({created.new_id}); }} }})()")
            page.wait_for_timeout(900)
        deleted = checker.verify_deleted(created.new_id)

        ok = created.passed and edited.passed and deleted.passed
        reporter.record_crud("Budget", checker.steps_passed, checker.steps_total)
        reporter.add_step(
            "Budget CRUD (API-verified)", "Budgets", "PASS" if ok else "FAIL",
            f"Create: {created.detail} | Edit: {edited.detail} | Delete: {deleted.detail}",
            screenshot_path=shot,
        )
    except Exception as ex:
        shot_err = screenshot_logger.capture(page, "budgets", "modal", "error", "fail", "fail")
        reporter.record_crud("Budget", checker.steps_passed, max(checker.steps_total, 1))
        reporter.add_step("Budget CRUD Test", "Budgets", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)
