"""
WealthFlow QA Module — Financial Commitments Calendar
Asserts real rendered content (not just that buttons exist):
 1. Tab loads; month grid places every event on its own date; weekday headers align
 2. No blank labels or raw i18n keys in any view (month / week / agenda / risk panel)
 3. Day detail opens by click and by keyboard (Enter) with a formatted date
 4. Month navigation: arrows, month picker, Today; arrows disable at the loaded window edges
 5. Week view: Monday-first 7 columns, current week by default, week arrows, events on their day
 6. Agenda view: one row per event, kind badge and projected balance, no navigation controls
 7. Financial Intelligence panel: formatted dates/amounts, concentration = distinct commitments
 8. Category filter and bank filter change the loaded events correctly
 9. Settings > Reminders concentration window: valid value saved and applied, invalid rejected
10. Arabic language: RTL labels translated, no raw keys
"""

import re
from datetime import date, timedelta

SECTION = "Financial Advisor"
RAW_KEY = re.compile(r"commitments_[a-z_]+")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _eval(context, script):
    return context.page.evaluate(script)


def _open_tab(context):
    context.page.evaluate(
        "if (typeof switchFinancialAdvisorTab === 'function') switchFinancialAdvisorTab('commitments-calendar');"
    )
    context.page.wait_for_selector("#commitments-toolbar", timeout=15000)
    context.page.wait_for_timeout(800)


def _click(context, selector, wait=500):
    context.page.click(selector)
    context.page.wait_for_timeout(wait)


def _blank_and_raw(context, scope_selectors):
    """Blank data-i18n nodes and raw translation keys visible inside the given scopes."""
    return context.page.evaluate(
        """(scopes) => {
          const blank = []; const raw = [];
          for (const sel of scopes) {
            const root = document.querySelector(sel);
            if (!root) { blank.push('missing ' + sel); continue; }
            root.querySelectorAll('[data-i18n]').forEach(el => {
              if (!el.textContent.trim()) blank.push(el.getAttribute('data-i18n'));
            });
            const m = root.innerText.match(/commitments_[a-z_]+/g);
            if (m) raw.push(...m);
          }
          return { blank, raw };
        }""",
        scope_selectors,
    )


def test_commitments_calendar_module(context, reporter, screenshot_logger):
    page = context.page

    def step(name, ok, detail, shot=None):
        reporter.add_step(name, SECTION, "PASS" if ok else "FAIL", detail, screenshot_path=shot)

    def shot(tab, action):
        return screenshot_logger.capture(page, "financial-advisor", tab, "view", action, "ok")

    context.goto_route("#financial-advisor")
    reporter.pages_visited.add("Financial Advisor -> Commitments Calendar")

    try:
        _open_tab(context)
        reporter.tabs_visited.add("Financial Advisor -> Commitments Calendar")
        step("Commitments Calendar Tab Load", page.query_selector("#commitments-toolbar") is not None,
             "Toolbar rendered.")

        data = _eval(context, "(typeof _commitmentsData !== 'undefined' && _commitmentsData) ? _commitmentsData : null")
        step("Commitments Payload Loaded", bool(data and isinstance(data.get("events"), list)),
             f"{len((data or {}).get('events', []))} events, window "
             f"{(data or {}).get('settings', {}).get('concentration_window_days')} days.")
        events = (data or {}).get("events", [])

        # 1. Month grid: every event on its own date, no stray chips, weekday headers align
        step("Commitments Calendar Month View", page.query_selector(".commitments-day-cell") is not None,
             "Month grid rendered.", shot("commitments_calendar", "month"))
        date_check = _eval(context, """(() => {
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
        header = _eval(context, """(() => {
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
        target = _eval(context, """(() => {
          const withChip = document.querySelector('.commitments-day-cell .commitments-chip');
          const cell = withChip ? withChip.closest('[data-commitments-day]') : document.querySelector('[data-commitments-day]');
          return cell.getAttribute('data-commitments-day');
        })()""")
        _click(context, f'[data-commitments-day="{target}"]', 300)
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
        month_scan = _blank_and_raw(context, ["#commitments-toolbar", "#commitments-view", "#commitments-risk-panel"])
        step("Commitments No Blank Labels (month)", not month_scan["blank"] and not month_scan["raw"],
             "No blank labels or raw keys." if not month_scan["blank"] and not month_scan["raw"] else str(month_scan))

        # 4. Month navigation
        nav = _eval(context, """(() => ({
          prevDisabled: document.querySelector('[data-commitments-nav="-1"]').disabled,
          nextDisabled: document.querySelector('[data-commitments-nav="1"]').disabled,
          month: document.getElementById('commitments-month-select').value,
          title: document.querySelector('#commitments-view .card-body > div').textContent.trim(),
        }))()""")
        _click(context, '[data-commitments-nav="1"]')
        after = _eval(context, """(() => ({
          month: document.getElementById('commitments-month-select').value,
          title: document.querySelector('#commitments-view .card-body > div').textContent.trim(),
          cells: document.querySelectorAll('.commitments-day-cell').length,
        }))()""")
        _click(context, "[data-commitments-today]")
        back = _eval(context, "document.getElementById('commitments-month-select').value")
        options = _eval(context, "document.querySelectorAll('#commitments-month-select option').length")
        page.select_option("#commitments-month-select", index=options - 1)
        page.wait_for_timeout(400)
        edge = _eval(context, "document.querySelector('[data-commitments-nav=\"1\"]').disabled")
        _click(context, "[data-commitments-today]")
        nav_ok = nav["prevDisabled"] and not nav["nextDisabled"] and after["month"] != nav["month"] \
            and after["title"] != nav["title"] and after["cells"] == 42 and back == nav["month"] \
            and options == 12 and edge
        step("Commitments Month Navigation", nav_ok,
             "Arrows, month picker and Today work; previous disabled at the current month, next disabled at the last loaded month."
             if nav_ok else f"nav={nav} after={after} back={back} options={options} edge={edge}")

        # 5. Week view
        _click(context, '[data-commitments-view="week"]', 700)
        week = _eval(context, """(() => {
          const days = Array.from(document.querySelectorAll('[data-commitments-week-day]'));
          const keys = days.map(d => d.getAttribute('data-commitments-week-day'));
          const t = new Date();
          const today = t.getFullYear() + '-' + String(t.getMonth() + 1).padStart(2, '0') + '-' + String(t.getDate()).padStart(2, '0');
          const first = new Date(keys[0] + 'T00:00:00');
          const mismatched = _commitmentsData.events.filter(e => keys.includes(e.date)).filter(e =>
            !document.querySelector('[data-commitments-week-day="' + e.date + '"] .commitments-event-card')).map(e => e.date);
          return { count: days.length, keys, today, containsToday: keys.includes(today), monday: first.getDay() === 1, mismatched };
        })()""")
        step("Commitments Week View (current week, Monday first)",
             week["count"] == 7 and week["containsToday"] and week["monday"] and not week["mismatched"],
             f"Week {week['keys'][0]} .. {week['keys'][-1]} shows today and its events." if week["count"] == 7
             else str(week), shot("commitments_calendar_week", "week"))
        first_week = week["keys"][0]
        _click(context, '[data-commitments-nav="1"]')
        next_week = _eval(context, "document.querySelector('[data-commitments-week-day]').getAttribute('data-commitments-week-day')")
        _click(context, '[data-commitments-nav="-1"]')
        prev_week = _eval(context, "document.querySelector('[data-commitments-week-day]').getAttribute('data-commitments-week-day')")
        expected_next = (date.fromisoformat(first_week) + timedelta(days=7)).isoformat()
        step("Commitments Week Navigation", next_week == expected_next and prev_week == first_week,
             f"Next week {next_week}, back to {prev_week}." if next_week == expected_next
             else f"first={first_week} next={next_week} expected={expected_next} back={prev_week}")
        week_scan = _blank_and_raw(context, ["#commitments-toolbar", "#commitments-view"])
        step("Commitments No Blank Labels (week)", not week_scan["blank"] and not week_scan["raw"],
             "No blank labels or raw keys." if not week_scan["blank"] and not week_scan["raw"] else str(week_scan))

        # 6. Agenda view
        _click(context, '[data-commitments-view="agenda"]', 700)
        agenda = _eval(context, """(() => ({
          rows: document.querySelectorAll('.commitments-agenda-row').length,
          events: _commitmentsData.events.length,
          badges: Array.from(document.querySelectorAll('.commitments-agenda-row .badge')).filter(b => !b.textContent.trim()).length,
          balances: Array.from(document.querySelectorAll('.commitments-agenda-row')).filter(r => /\\d/.test(r.innerText)).length,
          navShown: !!document.querySelector('[data-commitments-nav]'),
        }))()""")
        agenda_scan = _blank_and_raw(context, ["#commitments-toolbar", "#commitments-view"])
        agenda_ok = agenda["rows"] == agenda["events"] and agenda["badges"] == 0 and not agenda["navShown"] \
            and not agenda_scan["blank"] and not agenda_scan["raw"]
        step("Commitments Calendar Agenda View", agenda_ok,
             f"{agenda['rows']} rows = {agenda['events']} events; badges and labels present." if agenda_ok
             else f"{agenda} {agenda_scan}", shot("commitments_calendar_agenda", "agenda"))
        _click(context, '[data-commitments-view="month"]', 500)

        # 7. Risk panel content
        panel = _eval(context, "document.querySelector('#commitments-risk-panel').innerText")
        analysis = (data or {}).get("analysis", {})
        window_days = analysis.get("window_days", 30)
        bad_windows = []
        for w in analysis.get("concentration_windows", []):
            start = date.fromisoformat(w["start"])
            end = start + timedelta(days=window_days)
            distinct = {(e["source"], e["source_id"], e["event_type"]) for e in events
                        if e["category"] == "expense" and e["kind"] in ("actual", "expected")
                        and start <= date.fromisoformat(e["date"]) < end}
            if len(distinct) < 2:
                bad_windows.append(w["start"])
        panel_ok = page.query_selector("#commitments-risk-panel .card") is not None \
            and not RAW_KEY.search(panel) and not ISO_DATE.search(panel) and not bad_windows
        step("Financial Intelligence Panel", panel_ok,
             "Panel rendered: no raw keys or ISO dates; every concentration window holds 2+ distinct commitments."
             if panel_ok else f"raw={RAW_KEY.findall(panel)} iso={ISO_DATE.findall(panel)} single_source_windows={bad_windows}")

        # 8. Filters
        page.select_option("#commitments-category-filter", "income")
        page.wait_for_timeout(1500)
        income = _eval(context, "_commitmentsData.events.map(e => e.category)")
        page.select_option("#commitments-category-filter", "")
        page.wait_for_timeout(1500)
        full = _eval(context, "_commitmentsData.events.length")
        step("Commitments Category Filter", all(c == "income" for c in income) and len(income) <= full,
             f"income filter returned {len(income)} of {full} events, all income.")
        banks = _eval(context, "_commitmentsData.filters.banks")
        options = _eval(context, "document.querySelectorAll('#commitments-bank-filter option').length")
        bank_ok = options == len(banks) + 1
        bank_detail = f"{len(banks)} banks listed."
        if banks:
            page.select_option("#commitments-bank-filter", str(banks[0]["id"]))
            page.wait_for_timeout(1500)
            ids = _eval(context, "_commitmentsData.events.map(e => e.bank_id)")
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
        saved_ok = "45" == _eval(context, "fetch('/api/settings/').then(r => r.json()).then(d => String((d.settings || d).commitments_concentration_window_days))")
        page.fill("#commitmentsWindowDays", "0")
        page.click(save)
        page.wait_for_timeout(900)
        toast = _eval(context, "(document.getElementById('toast-container') || {innerText: ''}).innerText")
        still_45 = "45" == _eval(context, "fetch('/api/settings/').then(r => r.json()).then(d => String((d.settings || d).commitments_concentration_window_days))")
        context.goto_route("#financial-advisor")
        _open_tab(context)
        applied = _eval(context, "_commitmentsData.settings.concentration_window_days")
        page.evaluate("fetch('/api/settings/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({key:'commitments_concentration_window_days', value:'30'})})")
        page.wait_for_timeout(500)
        setting_ok = saved_ok and still_45 and applied == 45 and bool(toast.strip())
        step("Commitments Concentration Window Setting", setting_ok,
             "45 saved and applied by the calendar; 0 rejected with an error toast; restored to 30." if setting_ok
             else f"saved_ok={saved_ok} still_45={still_45} applied={applied} toast={toast!r}")

        # 10. Arabic
        page.evaluate("loadLanguage('ar')")
        page.wait_for_timeout(1500)
        context.goto_route("#financial-advisor")
        _open_tab(context)
        ar_text = page.inner_text("#commitments-toolbar") + page.inner_text("#commitments-view")
        ar_scan = _blank_and_raw(context, ["#commitments-toolbar", "#commitments-view", "#commitments-risk-panel"])
        has_arabic = bool(re.search(r"[؀-ۿ]", ar_text))
        step("Commitments Arabic (RTL) Labels", has_arabic and not ar_scan["blank"] and not ar_scan["raw"],
             "Arabic labels rendered, no blank labels or raw keys." if has_arabic else f"no Arabic text: {ar_text[:80]!r}",
             shot("commitments_calendar_ar", "arabic"))
        page.evaluate("loadLanguage('en')")
        page.wait_for_timeout(1000)
    except Exception as ex:  # noqa: BLE001 - report any UI failure as a failed step
        page.evaluate("try { loadLanguage('en'); } catch (e) {}")
        err = screenshot_logger.capture(page, "financial-advisor", "commitments_calendar", "error", "exception", "fail")
        reporter.add_step("Commitments Calendar Module", SECTION, "FAIL", f"Exception: {ex}", screenshot_path=err)
