"""Commitments Calendar E2E, part 3: filters, Settings > Reminders (window, first day of week), Arabic."""

import re

from tests.modules.commitments_calendar_support import blank_and_raw, click, eval_js, open_tab


def run_filters_settings_language(context, step, shot, state):
    page = context.page
    # 8. Filters
    page.select_option("#commitments-category-filter", "income")
    page.wait_for_timeout(1500)
    income = eval_js(context, "_commitmentsData.events.map(e => e.category)")
    page.select_option("#commitments-category-filter", "")
    page.wait_for_timeout(1500)
    full = eval_js(context, "_commitmentsData.events.length")
    step("Commitments Category Filter", all(c == "income" for c in income) and len(income) <= full,
         f"income filter returned {len(income)} of {full} events, all income.")
    banks = eval_js(context, "_commitmentsData.filters.banks")
    options = eval_js(context, "document.querySelectorAll('#commitments-bank-filter option').length")
    bank_ok = options == len(banks) + 1
    bank_detail = f"{len(banks)} banks listed."
    if banks:
        page.select_option("#commitments-bank-filter", str(banks[0]["id"]))
        page.wait_for_timeout(1500)
        ids = eval_js(context, "_commitmentsData.events.map(e => e.bank_id)")
        bank_ok = bank_ok and all(i == banks[0]["id"] for i in ids)
        bank_detail = f"bank {banks[0]['name']}: {len(ids)} events, all for that bank."
        page.select_option("#commitments-bank-filter", "")
        page.wait_for_timeout(1500)
    step("Commitments Bank Filter", bank_ok, bank_detail)

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
    page.evaluate("fetch('/api/settings/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({key:'commitments_concentration_window_days', value:'30'})})")
    page.wait_for_timeout(500)
    setting_ok = saved_ok and still_45 and applied == 45 and bool(toast.strip())
    step("Commitments Concentration Window Setting", setting_ok,
         "45 saved and applied by the calendar; 0 rejected with an error toast; restored to 30." if setting_ok
         else f"saved_ok={saved_ok} still_45={still_45} applied={applied} toast={toast!r}")

    # 9b. First day of the week (default Sunday; configurable on Settings > Reminders)
    default_start = eval_js(context, "_commitmentsData.settings.week_start_day")
    sunday_first = eval_js(context, "new Date(document.querySelector('.commitments-day-cell').dataset.commitmentsDay + 'T00:00:00').getDay()")
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
    page.evaluate("fetch('/api/settings/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({key:'commitments_week_start_day', value:'7'})}).then(r => window.__weekStartBad = r.status)")
    page.wait_for_timeout(600)
    rejected = eval_js(context, "window.__weekStartBad") == 400
    page.select_option("#commitmentsWeekStart", "0")
    page.click("#commitmentsWeekStart + button")
    page.wait_for_timeout(900)
    context.goto_route("#financial-advisor")
    open_tab(context)
    week_ok = default_start == 0 and sunday_first == 0 and monday_month == 1 and monday_week == 1 and rejected
    step("Commitments First Day of the Week Setting", week_ok,
         "Default Sunday; set to Monday -> month grid and week view start on Monday; 7 rejected; restored to Sunday."
         if week_ok else f"default={default_start} sunday_first={sunday_first} monday_month={monday_month} monday_week={monday_week} rejected={rejected}")

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
