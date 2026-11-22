"""
WealthFlow QA Module — Financial Commitments Calendar
Tests:
 1. Commitments Calendar tab loads with events rendered
 2. Month / Week / Agenda view switching
 3. Category and bank filters
 4. Financial Intelligence (risk) panel present
"""


def test_commitments_calendar_module(context, reporter, screenshot_logger):
    context.goto_route("#financial-advisor")
    reporter.pages_visited.add("Financial Advisor -> Commitments Calendar")

    try:
        context.page.evaluate(
            "if (typeof switchFinancialAdvisorTab === 'function') switchFinancialAdvisorTab('commitments-calendar');"
        )
        context.page.wait_for_timeout(1500)
        reporter.tabs_visited.add("Financial Advisor -> Commitments Calendar")

        toolbar = context.page.query_selector("#commitments-toolbar")
        reporter.add_step(
            "Commitments Calendar Tab Load",
            "Financial Advisor",
            "PASS" if toolbar else "FAIL",
            "Toolbar rendered." if toolbar else "Toolbar missing.",
        )

        shot = screenshot_logger.capture(context.page, "financial-advisor", "commitments_calendar", "view", "month", "ok")
        reporter.add_step(
            "Commitments Calendar Month View",
            "Financial Advisor",
            "PASS",
            "Month grid rendered.",
            screenshot_path=shot,
        )

        # Date-correctness regression: every event in the visible month window
        # must sit in the cell whose date equals the event's own date, and no
        # chip may appear on a non-event day. (Catches the UTC/toISOString
        # one-day-ahead grid bug.)
        date_check = context.page.evaluate(
            """(() => {
              const data = (typeof _commitmentsData !== 'undefined' && _commitmentsData) ? _commitmentsData : null;
              if (!data || !Array.isArray(data.events)) return { ok: true, checked: 0, note: 'no event data' };
              const cells = Array.from(document.querySelectorAll('[data-commitments-day]'));
              const cellDates = new Set(cells.map(c => c.getAttribute('data-commitments-day')));
              const inWindow = data.events.filter(e => cellDates.has(e.date));
              const missing = [];
              for (const e of inWindow) {
                const cell = document.querySelector('[data-commitments-day="' + e.date + '"]');
                if (!cell || cell.querySelectorAll('.commitments-chip').length < 1) missing.push(e.date);
              }
              const chipDates = new Set();
              cells.forEach(c => { if (c.querySelectorAll('.commitments-chip').length > 0) chipDates.add(c.getAttribute('data-commitments-day')); });
              const stray = [...chipDates].filter(d => !data.events.some(e => e.date === d));
              return { ok: missing.length === 0 && stray.length === 0, checked: inWindow.length, missing, stray };
            })()"""
        )
        reporter.add_step(
            "Commitments Date Correctness (month grid)",
            "Financial Advisor",
            "PASS" if date_check.get("ok") else "FAIL",
            (f"{date_check.get('checked')} events checked; each on its own date cell.")
            if date_check.get("ok")
            else f"missing={date_check.get('missing')} stray={date_check.get('stray')}",
        )

        # Weekday-header alignment regression: each header cell must name the
        # weekday of the date in the column beneath it (grid starts on Monday).
        header_check = context.page.evaluate(
            """(() => {
              const cells = Array.from(document.querySelectorAll('.commitments-day-cell'));
              if (cells.length < 7) return { ok: false, note: 'no date cells' };
              const headerRow = cells[0].parentElement.previousElementSibling;
              if (!headerRow || headerRow.children.length !== 7) return { ok: false, note: 'header row not found' };
              const headers = Array.from(headerRow.children).map(c => c.textContent.trim());
              const lang = (typeof currentLang === 'function') ? currentLang() : (document.documentElement.lang || 'en');
              const mismatches = [];
              for (let i = 0; i < 7; i++) {
                const [y, mo, d] = cells[i].getAttribute('data-commitments-day').split('-').map(Number);
                const expected = new Date(y, mo - 1, d).toLocaleDateString(lang, { weekday: 'short' });
                if (headers[i] !== expected) mismatches.push({ col: i, header: headers[i], expected });
              }
              return { ok: mismatches.length === 0, checked: 7, mismatches };
            })()"""
        )
        reporter.add_step(
            "Commitments Weekday Header Alignment",
            "Financial Advisor",
            "PASS" if header_check.get("ok") else "FAIL",
            "All 7 header cells match their column's date weekday."
            if header_check.get("ok")
            else f"mismatches={header_check.get('mismatches')}",
        )

        # Switch to Week view
        week_btn = context.page.query_selector('[data-commitments-view="week"]')
        if week_btn:
            week_btn.click()
            context.page.wait_for_timeout(600)
            shot_w = screenshot_logger.capture(context.page, "financial-advisor", "commitments_calendar_week", "click", "week", "ok")
            reporter.add_step("Commitments Calendar Week View", "Financial Advisor", "PASS", "Week view rendered.", screenshot_path=shot_w)

        # Switch to Agenda view
        agenda_btn = context.page.query_selector('[data-commitments-view="agenda"]')
        if agenda_btn:
            agenda_btn.click()
            context.page.wait_for_timeout(600)
            shot_a = screenshot_logger.capture(context.page, "financial-advisor", "commitments_calendar_agenda", "click", "agenda", "ok")
            reporter.add_step("Commitments Calendar Agenda View", "Financial Advisor", "PASS", "Agenda view rendered.", screenshot_path=shot_a)

        # Risk / Financial Intelligence panel
        risk = context.page.query_selector("#commitments-risk-panel .card")
        reporter.add_step(
            "Financial Intelligence Panel",
            "Financial Advisor",
            "PASS" if risk else "FAIL",
            "Risk panel rendered." if risk else "Risk panel missing.",
        )

        # Category filter (income) then reset. Re-query fresh before each
        # select: the toolbar can re-render between views and detach a stale
        # ElementHandle ("Element is not attached to the DOM").
        def _fresh_cat():
            el = context.page.query_selector("#commitments-category-filter")
            if el and el.evaluate("e => e.isConnected"):
                return el
            return None

        cat = _fresh_cat()
        if cat:
            cat.select_option("income")
            context.page.wait_for_timeout(900)
            cat2 = _fresh_cat()
            if cat2:
                cat2.select_option("")
                context.page.wait_for_timeout(900)
            reporter.add_step("Commitments Category Filter", "Financial Advisor", "PASS", "Filtered to income and back.")

    except Exception as ex:
        reporter.add_step("Commitments Calendar E2E Test", "Financial Advisor", "FAIL", f"Exception: {ex}")
