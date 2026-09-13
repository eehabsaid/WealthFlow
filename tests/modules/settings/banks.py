"""Settings module phase 1: Bank Setting CRUD. Split out of tests/modules/settings.py."""

from tests.core.data_generator import get_unique_bank_data
from tests.core.crud_verifier import CrudVerifier


def test_banks(context, reporter, screenshot_logger):
    # 1. Bank Setting CRUD — real, API-verified
    bank_data = get_unique_bank_data()
    bank_checker = CrudVerifier(context.page, api_list_url="/api/banks/", list_key="banks")
    try:
        context.page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('banks');")
        context.page.wait_for_timeout(500)

        before_ids = bank_checker.snapshot_ids()

        context.page.evaluate("if (typeof showBankModal === 'function') showBankModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Bank Setting Modal")
        shot1 = screenshot_logger.capture(context.page, "settings", "bank_modal", "showBankModal", "open", "ok")
        bank_checker.add_manual_step(context.page.query_selector("#bnName") is not None)

        if context.page.query_selector("#bnName"):
            context.page.fill("#bnName", bank_data["name"])
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(700)

        create_result = bank_checker.verify_created(before_ids, match_field="name", expected_value=bank_data["name"])

        new_name = bank_data["name"] + " Edited"
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showBankModal === 'function') showBankModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#bnName"):
                context.page.fill("#bnName", new_name)
                context.page.evaluate(f"(async () => {{ if (typeof saveBank === 'function') {{ await saveBank({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(700)
        edit_result = bank_checker.verify_field_updated(create_result.new_id, "name", new_name)

        if create_result.new_id is not None:
            context.page.evaluate(f"(async () => {{ if (typeof deleteBank === 'function') {{ await deleteBank({create_result.new_id}); }} }})()")
            context.page.wait_for_timeout(700)
        delete_result = bank_checker.verify_deleted(create_result.new_id)

        overall_pass = create_result.passed and edit_result.passed and delete_result.passed
        reporter.record_crud("Bank Setting", bank_checker.steps_passed, bank_checker.steps_total)
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
        reporter.add_step("Bank Setting CRUD (API-verified)", "Settings", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot1)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "settings", "bank_modal", "error", "fail", "fail")
        reporter.record_crud("Bank Setting", bank_checker.steps_passed, max(bank_checker.steps_total, 1))
        reporter.add_step("Bank Setting CRUD Test", "Settings", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)

