"""Settings module phase 3: Gold Type Setting soft-toggle CRUD. Split out of tests/modules/settings.py."""

from tests.core.crud_verifier import CrudVerifier
from tests.modules.settings.common import _uid


def test_gold_types(context, reporter, screenshot_logger):
    # 3. Gold Type Setting — real, API-verified. There is no delete
    # function for this entity: the "Active" select IS the deactivation
    # mechanism (soft toggle, not row removal), verified via field update.
    gt_checker = CrudVerifier(context.page, api_list_url="/api/settings/gold-types/", list_key="items")
    try:
        context.page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('gold-settings');")
        context.page.wait_for_timeout(500)

        before_ids = gt_checker.snapshot_ids()

        context.page.evaluate("if (typeof showGoldTypeModal === 'function') showGoldTypeModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Gold Type Setting Modal")
        shot_gt = screenshot_logger.capture(context.page, "settings", "gold_type_modal", "showGoldTypeModal", "open", "ok")
        gt_checker.add_manual_step(context.page.query_selector("#gstName") is not None)

        gt_name = "Test Gold Type " + _uid()
        if context.page.query_selector("#gstName"):
            context.page.fill("#gstName", gt_name)
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(700)

        create_result = gt_checker.verify_created(before_ids, match_field="name", expected_value=gt_name)

        # Deactivate via the Active select instead of a delete call.
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showGoldTypeModal === 'function') showGoldTypeModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#gstActive"):
                context.page.select_option("#gstActive", value="false")
                context.page.evaluate(f"(async () => {{ if (typeof saveGoldType === 'function') {{ await saveGoldType({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(700)
        deactivate_result = gt_checker.verify_field_updated(create_result.new_id, "is_active", False)

        overall_pass = create_result.passed and deactivate_result.passed
        reporter.record_crud("Gold Type Setting", gt_checker.steps_passed, gt_checker.steps_total)
        detail = f"Create: {create_result.detail} | Deactivate: {deactivate_result.detail}"
        reporter.add_step("Gold Type Setting CRUD (API-verified)", "Settings", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot_gt)
    except Exception as ex:
        reporter.record_crud("Gold Type Setting", gt_checker.steps_passed, max(gt_checker.steps_total, 1))
        reporter.add_step("Gold Type Setting Modal Test", "Settings", "FAIL", f"Exception: {ex}")

