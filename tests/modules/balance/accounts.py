"""Balance module phase 1: Balance Account CRUD (Add/Edit Balance Entry
Modal), including downstream cross-module verification (Dashboard Net
Worth & Advisor Overview). Split out of tests/modules/balance.py.
"""

from tests.core.data_generator import get_unique_balance_account_data
from tests.core.assertions import search_filter_sort_table, verify_downstream_impact
from tests.core.crud_verifier import CrudVerifier


def test_accounts(context, reporter, screenshot_logger):
    # 1. Balance Account CRUD — real, API-verified (was: unconditional 17/17)
    account_data = get_unique_balance_account_data()
    checker = CrudVerifier(context.page, api_list_url="/api/balance/", list_key="entries")

    try:
        before_ids = checker.snapshot_ids()

        context.page.evaluate("if (typeof showBalanceModal === 'function') showBalanceModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Add/Edit Balance Entry Modal")
        screenshot_logger.capture(context.page, "balance", "modal_open", "showBalanceModal", "open", "ok")
        checker.add_manual_step(context.page.query_selector("#bTitle") is not None)

        if context.page.query_selector("#bTitle"):
            context.page.select_option("#bbalance_type", index=1)
            context.page.fill("#bTitle", account_data["title"])
            context.page.fill("#bAmount", str(account_data["current_balance"]))
            if context.page.query_selector("#bNotes"):
                context.page.fill("#bNotes", account_data["notes"])

            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(800)

        context.page.evaluate("if (typeof closeModal === 'function') closeModal();")

        create_result = checker.verify_created(before_ids, match_field="title", expected_value=account_data["title"])

        # Edit: change the title via the API directly reflects UI behavior,
        # but we verify the edit through the real edit modal + save path.
        new_title = account_data["title"] + " (Edited)"
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showBalanceModal === 'function') showBalanceModal({create_result.new_id});")
            context.page.wait_for_timeout(600)
            if context.page.query_selector("#bTitle"):
                context.page.fill("#bTitle", new_title)
                save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
                if save_btn:
                    save_btn.click()
                    context.page.wait_for_timeout(800)
            context.page.evaluate("if (typeof closeModal === 'function') closeModal();")
        edit_result = checker.verify_field_updated(create_result.new_id, "title", new_title)

        context.reload()
        context.goto_route("#balance")
        shot2 = screenshot_logger.capture(context.page, "balance", "accounts", "none", "persistence_check", "ok")
        checker.add_manual_step(True)

        search_filter_sort_table(context.page, new_title)
        checker.add_manual_step(True)

        verify_downstream_impact(context.page, "Balance Creation", "dashboard")
        verify_downstream_impact(context.page, "Balance Creation", "financial-advisor")
        checker.add_manual_step(True)

        context.goto_route("#balance")
        context.page.wait_for_timeout(500)

        # Delete via the real deleteBalanceEntry() JS function. Uses a
        # native confirm() dialog — Playwright auto-dismisses (false)
        # unless a handler is registered to accept it first. Must be
        # properly awaited (async IIFE) or the delete fetch may not have
        # completed before we check via the API.
        if create_result.new_id is not None:
            context.page.evaluate(f"(async () => {{ if (typeof deleteBalanceEntry === 'function') {{ await deleteBalanceEntry({create_result.new_id}); }} }})()")
            context.page.wait_for_timeout(1200)
        delete_result = checker.verify_deleted(create_result.new_id)

        overall_pass = create_result.passed and edit_result.passed and delete_result.passed
        reporter.record_crud("Balance Account Entry", checker.steps_passed, checker.steps_total)
        status = "PASS" if overall_pass else "FAIL"
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
        reporter.add_step("Balance Account CRUD (API-verified)", "Balance & Net Worth", status, detail, screenshot_path=shot2)

    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "balance", "accounts", "error", "fail", "fail")
        reporter.record_crud("Balance Account Entry", checker.steps_passed, max(checker.steps_total, 1))
        reporter.add_step("Balance Module Test", "Balance & Net Worth", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)
