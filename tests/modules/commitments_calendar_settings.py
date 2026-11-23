"""Commitments Calendar E2E, part 4: Settings > Reminders (window, first day of week) and Arabic.

The user's own values are captured by the orchestrator (state["original"]) and restored exactly, never a default."""

import re

from tests.modules.commitments_calendar_state import WEEK_KEY, WINDOW_KEY, restore_settings
from tests.modules.commitments_calendar_support import blank_and_raw, click, eval_js, open_tab


_BAD_WEEK_START = """async () => {
  const csrf = (window.wfGetCsrfToken && window.wfGetCsrfToken()) || '';
  const r = await fetch('/api/settings/', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
                                            body: JSON.stringify({key: 'commitments_week_start_day', value: '7'})});
  let body = {};
  try { body = await r.json(); } catch (e) { body = {}; }
  return {csrf: csrf.length > 0, status: r.status, error: body.error || ''};
}"""


def run_settings_language(context, step, shot, state):
    page = context.page
    # 9. Concentration window setting (Settings > Reminders)
    context.goto_route("#settings-reminders")
    page.wait_for_selector("#commitmentsWindowDays", timeout=15000)
    save = "#commitmentsWindowDays + button"
    page.fill("#commitmentsWindowDays", "45")
    page.click(save)
    page.wait_for_timeout(900)
    saved_ok = "45" == eval_js(context, "fetch('/api/settings/').then(r => r.json()).then(d => String((d.settings || d).commitments_concentration_window_days))")
    page.fill("#commitmentsWindowDays", "0")
    page.click(save)
    page.wait_for_timeout(900)
    toast = eval_js(context, "(document.getElementById('toast-container') || {innerText: ''}).innerText")
    still_45 = "45" == eval_js(context, "fetch('/api/settings/').then(r => r.json()).then(d => String((d.settings || d).commitments_concentration_window_days))")
    context.goto_route("#financial-advisor")
    open_tab(context)
    applied = eval_js(context, "_commitmentsData.settings.concentration_window_days")
    restore_settings(context, state["original"], [WINDOW_KEY])
    page.wait_for_timeout(500)
    setting_ok = saved_ok and still_45 and applied == 45 and bool(toast.strip())
    step("Commitments Concentration Window Setting", setting_ok,
         "45 saved and applied by the calendar; 0 rejected with an error toast; original value restored." if setting_ok
         else f"saved_ok={saved_ok} still_45={still_45} applied={applied} toast={toast!r}")

    # 9b. First day of the week (default Sunday; configurable on Settings > Reminders)
    expected_start = int(state["original"][WEEK_KEY] or 0)  # the user's own first day (default Sunday when unset)
    default_start = eval_js(context, "_commitmentsData.settings.week_start_day")
    first_day = eval_js(context, "new Date(document.querySelector('.commitments-day-cell').dataset.commitmentsDay + 'T00:00:00').getDay()")
    context.goto_route("#settings-reminders")
    page.wait_for_selector("#commitmentsWeekStart", timeout=15000)
    page.select_option("#commitmentsWeekStart", "1")
    page.click("#commitmentsWeekStart + button")
    page.wait_for_timeout(900)
    context.goto_route("#financial-advisor")
    open_tab(context)
    monday_month = eval_js(context, "new Date(document.querySelector('.commitments-day-cell').dataset.commitmentsDay + 'T00:00:00').getDay()")
    click(context, '[data-commitments-view="week"]', 600)
    monday_week = eval_js(context, "new Date(document.querySelector('[data-commitments-week-day]').dataset.commitmentsWeekDay + 'T00:00:00').getDay()")
    context.goto_route("#settings-reminders")
    page.wait_for_selector("#commitmentsWeekStart", timeout=15000)
    bad = page.evaluate(_BAD_WEEK_START)  # carries a valid CSRF token, so a 400 is the validation answer, not a CSRF 403
    rejected = bad["csrf"] and bad["status"] == 400 and bad["error"] == "invalid value for commitments_week_start_day"
    restore_settings(context, state["original"], [WEEK_KEY])
    page.wait_for_timeout(600)
    context.goto_route("#financial-advisor")
    open_tab(context)
    week_ok = default_start == expected_start and first_day == expected_start and monday_month == 1 and monday_week == 1 and rejected
    step("Commitments First Day of the Week Setting", week_ok,
         "Original first day shown; set to Monday -> month grid and week view start on Monday; 7 rejected with HTTP 400 and the validation error (valid CSRF token sent); original restored."
         if week_ok else f"default={default_start} expected={expected_start} first_day={first_day} monday_month={monday_month} monday_week={monday_week} rejected={rejected} bad={bad}")

    # 10. Arabic
    page.evaluate("loadLanguage('ar')")
    page.wait_for_timeout(1500)
    context.goto_route("#financial-advisor")
    open_tab(context)
    ar_text = page.inner_text("#commitments-toolbar") + page.inner_text("#commitments-view")
    ar_scan = blank_and_raw(context, ["#commitments-toolbar", "#commitments-view", "#commitments-risk-panel"])
    has_arabic = bool(re.search(r"[؀-ۿ]", ar_text))
    step("Commitments Arabic (RTL) Labels", has_arabic and not ar_scan["blank"] and not ar_scan["raw"],
         "Arabic labels rendered, no blank labels or raw keys." if has_arabic else f"no Arabic text: {ar_text[:80]!r}",
         shot("commitments_calendar_ar", "arabic"))
    page.evaluate("loadLanguage('en')")
    page.wait_for_timeout(1000)
