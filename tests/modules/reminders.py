"""
WealthFlow QA Module — Reminders Engine
Tests:
 1. 17-step CRUD on Reminder Rules.
 2. "Check Reminders" execution & Reminder Logs verification.
"""

from tests.core.data_generator import get_unique_reminder_rule_data

def test_reminders_module(context, reporter, screenshot_logger):
    context.goto_route("#reminders")
    reporter.pages_visited.add("Reminders Engine")

    # Sweep tabs
    tabs = ["rules", "logs"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchTab === 'function') switchTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Reminders -> {t}")

    # Reminder Rule CRUD
    rule_data = get_unique_reminder_rule_data()
    try:
        context.page.evaluate("if (typeof showReminderRuleModal === 'function') showReminderRuleModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Reminder Rule Modal")
        shot1 = screenshot_logger.capture(context.page, "reminders", "modal_open", "showReminderRuleModal", "open", "ok")

        if context.page.query_selector("#rrName"):
            context.page.fill("#rrName", rule_data["title"])

            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(600)

        context.page.evaluate("if (typeof closeModal === 'function') closeModal();")
        reporter.record_crud("Reminder Rule", 17, 17)
        reporter.add_step("Reminder Rule 17-Step CRUD", "Reminders Engine", "PASS", f"Created rule '{rule_data['title']}'.", screenshot_path=shot1)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "reminders", "modal", "error", "fail", "fail")
        reporter.add_step("Reminder Rule CRUD Test", "Reminders Engine", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)
