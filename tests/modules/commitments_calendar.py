"""
WealthFlow QA Module — Financial Commitments Calendar
Asserts real rendered content (not just that buttons exist). Orchestrator; parts:
  commitments_calendar.py           1-4: tab load, month grid correctness, day detail, month navigation
  commitments_calendar_views.py     5-7: week view, agenda view, Financial Intelligence panel
  commitments_calendar_today.py     today's box highlighted (month + week)
  commitments_calendar_filters.py   8: category filter, bank filter (real events, API fallback data)
  commitments_calendar_settings.py  9-10: Settings > Reminders (window, first day), Arabic
  commitments_calendar_state.py     capture/restore the user's ORIGINAL settings
Plus: no JavaScript errors while using the calendar, and the user's settings are always restored.
"""

from tests.modules.commitments_calendar_filters import run_filters
from tests.modules.commitments_calendar_settings import run_settings_language
from tests.modules.commitments_calendar_state import read_settings, restore_settings
from tests.modules.commitments_calendar_today import run_today_highlight
from tests.modules.commitments_calendar_support import ISO_DATE, blank_and_raw, click, eval_js, open_tab
from tests.modules.commitments_calendar_views import run_week_agenda_risk

SECTION = "Financial Advisor"


def test_commitments_calendar_module(context, reporter, screenshot_logger):
    page = context.page
    js_errors = []
    original = None
    page.on("pageerror", lambda e: js_errors.append(str(e)))

    def step(name, ok, detail, shot=None):
        reporter.add_step(name, SECTION, "PASS" if ok else "FAIL", detail, screenshot_path=shot)

    def shot(tab, action):
        return screenshot_logger.capture(page, "financial-advisor", tab, "view", action, "ok")

    context.goto_route("#financial-advisor")
    reporter.pages_visited.add("Financial Advisor -> Commitments Calendar")

    try:
        original = read_settings(context)  # the user's own values (None = nothing stored), restored in `finally`
        open_tab(context)
        reporter.tabs_visited.add("Financial Advisor -> Commitments Calendar")
        step("Commitments Calendar Tab Load", page.query_selector("#commitments-toolbar") is not None,
             "Toolbar rendered.")

        data = eval_js(context, "(typeof _commitmentsData !== 'undefined' && _commitmentsData) ? _commitmentsData : null")
        step("Commitments Payload Loaded", bool(data and isinstance(data.get("events"), list)),
             f"{len((data or {}).get('events', []))} events, window "
             f"{(data or {}).get('settings', {}).get('concentration_window_days')} days.")
        events = (data or {}).get("events", [])
        state = {"data": data, "events": events, "original": original}

        run_month_sections(context, step, shot, state)
        run_today_highlight(context, step, shot)
        run_week_agenda_risk(context, step, shot, state)
        run_filters(context, step, shot, state)
        run_settings_language(context, step, shot, state)
        step("Commitments No JavaScript Errors", not js_errors, "; ".join(js_errors)[:200] or "No page errors raised.")
    except Exception as ex:  # noqa: BLE001 - report any UI failure as a failed step
        page.evaluate("try { loadLanguage('en'); } catch (e) {}")
        err = screenshot_logger.capture(page, "financial-advisor", "commitments_calendar", "error", "exception", "fail")
        reporter.add_step("Commitments Calendar Module", SECTION, "FAIL", f"Exception: {ex}", screenshot_path=err)
    finally:
        if original is not None:
            try:
                restore_settings(context, original)
                page.wait_for_timeout(500)
                after = read_settings(context)
                step("Commitments Settings Restored To Originals", after == original,
                     f"Restored exactly: {original}" if after == original else f"original={original} after={after}")
            except Exception as ex:  # noqa: BLE001 - report a failed cleanup instead of hiding it
                step("Commitments Settings Restored To Originals", False, f"Restore failed: {ex}")


def run_month_sections(context, step, shot, state):
    page = context.page
    events = state["events"]
    # 1. Month grid: every event on its own date, no stray chips, weekday headers align
    step("Commitments Calendar Month View", page.query_selector(".commitments-day-cell") is not None,
         "Month grid rendered.", shot("commitments_calendar", "month"))
    date_check = eval_js(context, """(() => {
      const data = _commitmentsData;
      const cells = Array.from(document.querySelectorAll('[data-commitments-day]'));
      const cellDates = new Set(cells.map(c => c.getAttribute('data-commitments-day')));
      const inWindow = data.events.filter(e => cellDates.has(e.date));
      const missing = inWindow.filter(e => {
        const cell = document.querySelector('[data-commitments-day="' + e.date + '"]');
        return !cell || cell.querySelectorAll('.commitments-chip').length < 1;
      }).map(e => e.date);
      const stray = cells.filter(c => c.querySelectorAll('.commitments-chip').length > 0)
        .map(c => c.getAttribute('data-commitments-day'))
        .filter(d => !data.events.some(e => e.date === d));
      return { ok: !missing.length && !stray.length, checked: inWindow.length, missing, stray };
    })()""")
    step("Commitments Date Correctness (month grid)", date_check["ok"],
         f"{date_check['checked']} events checked; each on its own date cell."
         if date_check["ok"] else f"missing={date_check['missing']} stray={date_check['stray']}")
    header = eval_js(context, """(() => {
      const cells = Array.from(document.querySelectorAll('.commitments-day-cell'));
      const row = cells[0].parentElement.previousElementSibling;
      const headers = Array.from(row.children).map(c => c.textContent.trim());
      const bad = [];
      for (let i = 0; i < 7; i++) {
        const [y, m, d] = cells[i].getAttribute('data-commitments-day').split('-').map(Number);
        const expected = new Date(y, m - 1, d).toLocaleDateString(currentLang(), { weekday: 'short' });
        if (headers[i] !== expected) bad.push({ col: i, header: headers[i], expected });
      }
      return { ok: headers.length === 7 && !bad.length, bad };
    })()""")
    step("Commitments Weekday Header Alignment", header["ok"],
         "All 7 headers match their column's weekday." if header["ok"] else f"mismatches={header['bad']}")

    # 2 + 3. Day detail by click and by keyboard
    target = eval_js(context, """(() => {
      const withChip = document.querySelector('.commitments-day-cell .commitments-chip');
      const cell = withChip ? withChip.closest('[data-commitments-day]') : document.querySelector('[data-commitments-day]');
      return cell.getAttribute('data-commitments-day');
    })()""")
    click(context, f'[data-commitments-day="{target}"]', 300)
    by_click = page.inner_text("#commitments-day-detail")
    page.focus(f'[data-commitments-day="{target}"]')
    page.evaluate("document.getElementById('commitments-day-detail').innerHTML = ''")
    page.keyboard.press("Enter")
    page.wait_for_timeout(300)
    by_key = page.inner_text("#commitments-day-detail")
    has_event = any(e["date"] == target for e in events)
    detail_ok = bool(by_click.strip()) and by_click == by_key and not ISO_DATE.search(by_click) \
        and (not has_event or page.query_selector("#commitments-day-detail .commitments-event-card") is not None)
    step("Commitments Day Detail (click + keyboard)", detail_ok,
         f"Day {target}: same content by click and Enter, date formatted (no ISO)." if detail_ok
         else f"click={by_click!r} key={by_key!r}")

    # Month view labels
    month_scan = blank_and_raw(context, ["#commitments-toolbar", "#commitments-view", "#commitments-risk-panel"])
    step("Commitments No Blank Labels (month)", not month_scan["blank"] and not month_scan["raw"],
         "No blank labels or raw keys." if not month_scan["blank"] and not month_scan["raw"] else str(month_scan))

    # 4. Month navigation
    nav = eval_js(context, """(() => ({
      prevDisabled: document.querySelector('[data-commitments-nav="-1"]').disabled,
      nextDisabled: document.querySelector('[data-commitments-nav="1"]').disabled,
      month: document.getElementById('commitments-month-select').value,
      title: document.querySelector('#commitments-view .card-body > div').textContent.trim(),
    }))()""")
    click(context, '[data-commitments-nav="1"]')
    after = eval_js(context, """(() => ({
      month: document.getElementById('commitments-month-select').value,
      title: document.querySelector('#commitments-view .card-body > div').textContent.trim(),
      cells: document.querySelectorAll('.commitments-day-cell').length,
    }))()""")
    click(context, "[data-commitments-today]")
    back = eval_js(context, "document.getElementById('commitments-month-select').value")
    options = eval_js(context, "document.querySelectorAll('#commitments-month-select option').length")
    page.select_option("#commitments-month-select", index=options - 1)
    page.wait_for_timeout(400)
    edge = eval_js(context, "document.querySelector('[data-commitments-nav=\"1\"]').disabled")
    click(context, "[data-commitments-today]")
    nav_ok = nav["prevDisabled"] and not nav["nextDisabled"] and after["month"] != nav["month"] \
        and after["title"] != nav["title"] and after["cells"] == 42 and back == nav["month"] \
        and options == 12 and edge
    step("Commitments Month Navigation", nav_ok,
         "Arrows, month picker and Today work; previous disabled at the current month, next disabled at the last loaded month."
         if nav_ok else f"nav={nav} after={after} back={back} options={options} edge={edge}")

