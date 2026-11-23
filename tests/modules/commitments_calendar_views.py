"""Commitments Calendar E2E, part 2: week view, agenda view, Financial Intelligence panel."""

from datetime import date, timedelta

from tests.modules.commitments_calendar_support import ISO_DATE, RAW_KEY, blank_and_raw, click, eval_js


def run_week_agenda_risk(context, step, shot, state):
    page = context.page
    data = state["data"]
    events = state["events"]
    # 5. Week view
    click(context, '[data-commitments-view="week"]', 700)
    week = eval_js(context, """(() => {
      const days = Array.from(document.querySelectorAll('[data-commitments-week-day]'));
      const keys = days.map(d => d.getAttribute('data-commitments-week-day'));
      const t = new Date();
      const today = t.getFullYear() + '-' + String(t.getMonth() + 1).padStart(2, '0') + '-' + String(t.getDate()).padStart(2, '0');
      const first = new Date(keys[0] + 'T00:00:00');
      const mismatched = _commitmentsData.events.filter(e => keys.includes(e.date)).filter(e =>
        !document.querySelector('[data-commitments-week-day="' + e.date + '"] .commitments-event-card')).map(e => e.date);
      return { count: days.length, keys, today, containsToday: keys.includes(today), startsOnSetting: first.getDay() === _commitmentsData.settings.week_start_day, mismatched };
    })()""")
    step("Commitments Week View (current week, configured first day)",
         week["count"] == 7 and week["containsToday"] and week["startsOnSetting"] and not week["mismatched"],
         f"Week {week['keys'][0]} .. {week['keys'][-1]} shows today and its events." if week["count"] == 7
         else str(week), shot("commitments_calendar_week", "week"))
    first_week = week["keys"][0]
    click(context, '[data-commitments-nav="1"]')
    next_week = eval_js(context, "document.querySelector('[data-commitments-week-day]').getAttribute('data-commitments-week-day')")
    click(context, '[data-commitments-nav="-1"]')
    prev_week = eval_js(context, "document.querySelector('[data-commitments-week-day]').getAttribute('data-commitments-week-day')")
    expected_next = (date.fromisoformat(first_week) + timedelta(days=7)).isoformat()
    step("Commitments Week Navigation", next_week == expected_next and prev_week == first_week,
         f"Next week {next_week}, back to {prev_week}." if next_week == expected_next
         else f"first={first_week} next={next_week} expected={expected_next} back={prev_week}")
    week_scan = blank_and_raw(context, ["#commitments-toolbar", "#commitments-view"])
    step("Commitments No Blank Labels (week)", not week_scan["blank"] and not week_scan["raw"],
         "No blank labels or raw keys." if not week_scan["blank"] and not week_scan["raw"] else str(week_scan))

    # 6. Agenda view
    click(context, '[data-commitments-view="agenda"]', 700)
    agenda = eval_js(context, """(() => {
      const rows = Array.from(document.querySelectorAll('.commitments-agenda-row'));
      const label = t('commitments_projected_balance');
      const digits = (x) => String(x).replace(/[^0-9]/g, '');
      const bad = [];
      let checked = 0;
      _commitmentsData.events.forEach((e, i) => {
        if (e.projected_balance === undefined || !rows[i]) return;
        checked++;
        const cell = rows[i].children[2].children[1].innerText;
        const value = cell.replace(label, '').trim();
        const okLabel = cell.includes(label);
        const okNumber = /\\d/.test(value) && !/NaN|undefined|null/.test(value) && digits(value) === digits(_money(e.projected_balance));
        if (!okLabel || !okNumber) bad.push(e.date + ' ' + e.event_type + ' payload=' + e.projected_balance + ' shown=' + cell);
      });
      return {
        rows: rows.length,
        events: _commitmentsData.events.length,
        badges: Array.from(document.querySelectorAll('.commitments-agenda-row .badge')).filter(b => !b.textContent.trim()).length,
        withBalance: _commitmentsData.events.filter(e => e.projected_balance !== undefined).length,
        checked, bad: bad.slice(0, 3),
        navShown: !!document.querySelector('[data-commitments-nav]'),
      };
    })()""")
    agenda_scan = blank_and_raw(context, ["#commitments-toolbar", "#commitments-view"])
    agenda_ok = agenda["rows"] == agenda["events"] and agenda["badges"] == 0 and not agenda["navShown"] \
        and agenda["checked"] == agenda["withBalance"] > 0 and not agenda["bad"] \
        and not agenda_scan["blank"] and not agenda_scan["raw"]
    step("Commitments Calendar Agenda View", agenda_ok,
         f"{agenda['rows']} rows = {agenda['events']} events; {agenda['checked']} projected balances rendered (label + number) "
         f"and equal to the payload." if agenda_ok else f"{agenda} {agenda_scan}", shot("commitments_calendar_agenda", "agenda"))
    click(context, '[data-commitments-view="month"]', 500)

    # 7. Risk panel content
    panel = eval_js(context, "document.querySelector('#commitments-risk-panel').innerText")
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

