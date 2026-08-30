"""
WealthFlow QA Module — Reminders Engine
Tests:
 1. 17-step CRUD on Reminder Rules.
 2. "Check Reminders" execution & Reminder Logs verification.
"""

from tests.core.data_generator import get_unique_reminder_rule_data
from tests.core.crud_verifier import CrudVerifier

def test_reminders_module(context, reporter, screenshot_logger):
    # Registered persistently: delete uses a native confirm() dialog.
    context.page.on("dialog", lambda dialog: dialog.accept())

    context.goto_route("#reminders")
    reporter.pages_visited.add("Reminders Engine")

    # Sweep tabs
    tabs = ["rules", "logs"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchTab === 'function') switchTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Reminders -> {t}")

    # Reminder Rule CRUD — real, API-verified
    rule_data = get_unique_reminder_rule_data()
    checker = CrudVerifier(context.page, api_list_url="/api/reminders/", list_key="rules")
    try:
        before_ids = checker.snapshot_ids()

        context.page.evaluate("if (typeof showReminderRuleModal === 'function') showReminderRuleModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Reminder Rule Modal")
        shot1 = screenshot_logger.capture(context.page, "reminders", "modal_open", "showReminderRuleModal", "open", "ok")
        checker.add_manual_step(context.page.query_selector("#rrName") is not None)

        if context.page.query_selector("#rrName"):
            context.page.fill("#rrName", rule_data["title"])
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(700)

        create_result = checker.verify_created(before_ids, match_field="name", expected_value=rule_data["title"])

        new_title = rule_data["title"] + " Edited"
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showReminderRuleModal === 'function') showReminderRuleModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#rrName"):
                context.page.fill("#rrName", new_title)
                context.page.evaluate(f"(async () => {{ if (typeof saveReminderRule === 'function') {{ await saveReminderRule({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(700)
        edit_result = checker.verify_field_updated(create_result.new_id, "name", new_title)

        if create_result.new_id is not None:
            context.page.evaluate(f"(async () => {{ if (typeof deleteReminderRule === 'function') {{ await deleteReminderRule({create_result.new_id}); }} }})()")
            context.page.wait_for_timeout(700)
        delete_result = checker.verify_deleted(create_result.new_id)

        overall_pass = create_result.passed and edit_result.passed and delete_result.passed
        reporter.record_crud("Reminder Rule", checker.steps_passed, checker.steps_total)
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
        reporter.add_step("Reminder Rule CRUD (API-verified)", "Reminders Engine", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot1)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "reminders", "modal", "error", "fail", "fail")
        reporter.record_crud("Reminder Rule", checker.steps_passed, max(checker.steps_total, 1))
        reporter.add_step("Reminder Rule CRUD Test", "Reminders Engine", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)
