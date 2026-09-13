"""Settings module phase 4: Gold Purity Setting soft-toggle CRUD. Split out of tests/modules/settings.py."""

from tests.core.crud_verifier import CrudVerifier
from tests.modules.settings.common import _uid


def test_gold_purities(context, reporter, screenshot_logger):
    # 4. Gold Purity Setting — same soft-toggle pattern as Gold Type.
    gp_checker = CrudVerifier(context.page, api_list_url="/api/settings/gold-purities/", list_key="items")
    try:
        context.page.evaluate("if (typeof showGoldPurityModal === 'function') showGoldPurityModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Gold Purity Setting Modal")
        shot_gp = screenshot_logger.capture(context.page, "settings", "gold_purity_modal", "showGoldPurityModal", "open", "ok")
        gp_checker.add_manual_step(context.page.query_selector("#gspKey") is not None)

        before_ids = gp_checker.snapshot_ids()
        gp_key = _uid()[:2] + "k"
        gp_label = gp_key.upper()
        if context.page.query_selector("#gspKey"):
            context.page.fill("#gspKey", gp_key)
            context.page.fill("#gspLabel", gp_label)
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(700)

        create_result = gp_checker.verify_created(before_ids, match_field="key", expected_value=gp_key)

        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showGoldPurityModal === 'function') showGoldPurityModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#gspActive"):
                context.page.select_option("#gspActive", value="false")
                context.page.evaluate(f"(async () => {{ if (typeof saveGoldPurity === 'function') {{ await saveGoldPurity({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(700)
        deactivate_result = gp_checker.verify_field_updated(create_result.new_id, "is_active", False)

        overall_pass = create_result.passed and deactivate_result.passed
        reporter.record_crud("Gold Purity Setting", gp_checker.steps_passed, gp_checker.steps_total)
        detail = f"Create: {create_result.detail} | Deactivate: {deactivate_result.detail}"
        reporter.add_step("Gold Purity Setting CRUD (API-verified)", "Settings", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot_gp)
    except Exception as ex:
        reporter.add_step("Gold Settings Modal Test", "Settings", "FAIL", f"Exception: {ex}")

