"""Settings module phase 2: Currency Setting CRUD. Split out of tests/modules/settings.py."""

from tests.core.crud_verifier import CrudVerifier
from tests.modules.settings.common import _uid


def test_currencies(context, reporter, screenshot_logger):
    # 2. Currency Setting CRUD — real, API-verified
    curr_checker = CrudVerifier(context.page, api_list_url="/api/currencies/", list_key="currencies")
    try:
        context.page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('currencies');")
        context.page.wait_for_timeout(500)

        before_ids = curr_checker.snapshot_ids()

        context.page.evaluate("if (typeof showCurrencyModal === 'function') showCurrencyModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Currency Setting Modal")
        shot_curr = screenshot_logger.capture(context.page, "settings", "currency_modal", "showCurrencyModal", "open", "ok")
        curr_checker.add_manual_step(context.page.query_selector("#curCode") is not None)

        curr_code = "T" + _uid()[:2]
        if context.page.query_selector("#curCode"):
            context.page.fill("#curCode", curr_code)
            if context.page.query_selector("#curSymbol"):
                context.page.fill("#curSymbol", "T")
            if context.page.query_selector("#curName"):
                context.page.fill("#curName", "Test Currency " + _uid())
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(700)

        create_result = curr_checker.verify_created(before_ids, match_field="code", expected_value=curr_code)

        new_symbol = "X"
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showCurrencyModal === 'function') showCurrencyModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#curSymbol"):
                context.page.fill("#curSymbol", new_symbol)
                context.page.evaluate(f"(async () => {{ if (typeof saveCurrency === 'function') {{ await saveCurrency({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(700)
        edit_result = curr_checker.verify_field_updated(create_result.new_id, "symbol", new_symbol)

        if create_result.new_id is not None:
            context.page.evaluate(f"(async () => {{ if (typeof deleteCurrency === 'function') {{ await deleteCurrency({create_result.new_id}); }} }})()")
            context.page.wait_for_timeout(700)
        delete_result = curr_checker.verify_deleted(create_result.new_id)

        overall_pass = create_result.passed and edit_result.passed and delete_result.passed
        reporter.record_crud("Currency Setting", curr_checker.steps_passed, curr_checker.steps_total)
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
        reporter.add_step("Currency Setting CRUD (API-verified)", "Settings", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot_curr)
    except Exception as ex:
        reporter.record_crud("Currency Setting", curr_checker.steps_passed, max(curr_checker.steps_total, 1))
        reporter.add_step("Currency Setting Modal Test", "Settings", "FAIL", f"Exception: {ex}")

