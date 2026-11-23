"""Commitments Calendar E2E, part 3: category filter and a bank filter that must prove real events.

The bank filter uses a bank that actually has events. If none does, it creates deterministic test data through the
API (a bank + a recurring bill linked to it) and removes both afterwards.
"""

from datetime import date, timedelta

from tests.modules.commitments_calendar_support import click, eval_js, open_tab

_API = """async ([method, url, body]) => {
  const csrf = (window.wfGetCsrfToken && window.wfGetCsrfToken()) || '';
  const r = await fetch(url, {method, headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
                              body: body ? JSON.stringify(body) : undefined});
  let data = null; try { data = await r.json(); } catch (e) {}
  return {status: r.status, data};
}"""
_ROWS = """(() => Array.from(document.querySelectorAll('.commitments-agenda-row')).map(r => r.innerText))()"""


def _api(context, method, url, body=None):
    return context.page.evaluate(_API, [method, url, body])


def _create_fixture(context):
    """A bank with one upcoming recurring bill linked to it. Returns (bank_id, recurring_id) or raises."""
    bank = _api(context, "POST", "/api/banks/", {"name": "E2E Calendar Bank"})
    bank_id = (bank["data"] or {}).get("id") or (bank["data"] or {}).get("bank", {}).get("id")
    if bank["status"] not in (200, 201) or not bank_id:
        raise AssertionError(f"fixture bank not created: {bank}")
    start = (date.today() + timedelta(days=3)).isoformat()
    rec = _api(context, "POST", "/api/recurring-transactions/", {
        "name": "E2E Calendar Bill", "amount": 123, "frequency": "monthly", "interval": 1,
        "start_date": start, "bank_id": bank_id, "payment_method": "Bank"})
    rec_id = (rec["data"] or {}).get("id")
    if rec["status"] not in (200, 201) or not rec_id:
        _api(context, "DELETE", f"/api/banks/{bank_id}/")
        raise AssertionError(f"fixture recurring bill not created: {rec}")
    return bank_id, rec_id


def _bank_with_events(context):
    return eval_js(context, """(() => {
      const counts = {};
      _commitmentsData.events.forEach(e => { if (e.bank_id) counts[e.bank_id] = (counts[e.bank_id] || 0) + 1; });
      const hit = (_commitmentsData.filters.banks || []).find(b => counts[b.id]);
      return hit ? {id: hit.id, name: hit.name, total: counts[hit.id]} : null;
    })()""")


def _check_bank_filter(context, step, shot, bank):
    page = context.page
    full = eval_js(context, "_commitmentsData.events.map(e => [e.date, e.event_type, e.source, e.source_id].join('|'))")
    expected = eval_js(context, f"_commitmentsData.events.filter(e => e.bank_id === {int(bank['id'])}).length")
    page.select_option("#commitments-bank-filter", str(bank["id"]))
    page.wait_for_timeout(1500)
    events = eval_js(context, "_commitmentsData.events.map(e => ({k: [e.date, e.event_type, e.source, e.source_id].join('|'), bank_id: e.bank_id, label: _commitmentsEventLabel(e)}))")
    wrong = [e for e in events if e["bank_id"] != bank["id"]]
    subset = all(e["k"] in full for e in events)
    # rendered: the agenda lists every returned event (in order) and nothing else
    click(context, '[data-commitments-view="agenda"]', 700)
    rows = eval_js(context, _ROWS)
    missing = [e["label"] for i, e in enumerate(events) if i >= len(rows) or e["label"] not in rows[i]]
    rendered = len(rows) == len(events) and not missing
    click(context, '[data-commitments-view="month"]', 500)
    chips_ok = eval_js(context, """(() => {
      const shown = _commitmentsData.events.filter(e => document.querySelector(`[data-commitments-day="${e.date}"]`));
      return shown.every(e => document.querySelector(`[data-commitments-day="${e.date}"] .commitments-chip, [data-commitments-day="${e.date}"] [data-commitments-event]`) !== null);
    })()""")
    ok = bool(events) and not wrong and subset and rendered and chips_ok and len(events) == expected
    step("Commitments Bank Filter", ok,
         f"bank {bank['name']}: {len(events)} events (>0, = the {expected} unfiltered ones for it), every one has bank_id {bank['id']}, agenda renders all {len(rows)}."
         if ok else f"events={len(events)} expected={expected} wrong_bank={len(wrong)} subset={subset} agenda_rows={len(rows)} missing={missing[:3]} chips_ok={chips_ok}",
         shot("commitments_calendar_bank", "bank-filter"))
    page.select_option("#commitments-bank-filter", "")
    page.wait_for_timeout(1500)


def run_filters(context, step, shot, state):
    page = context.page
    page.select_option("#commitments-category-filter", "income")
    page.wait_for_timeout(1500)
    income = eval_js(context, "_commitmentsData.events.map(e => e.category)")
    page.select_option("#commitments-category-filter", "")
    page.wait_for_timeout(1500)
    full = eval_js(context, "_commitmentsData.events.length")
    step("Commitments Category Filter", bool(income) and all(c == "income" for c in income) and len(income) <= full,
         f"income filter returned {len(income)} of {full} events, all income.")

    banks = eval_js(context, "_commitmentsData.filters.banks")
    options = eval_js(context, "document.querySelectorAll('#commitments-bank-filter option').length")
    created = None
    try:
        bank = _bank_with_events(context)
        if not bank:  # deterministic fallback: create data through the API, clean up below
            created = _create_fixture(context)
            open_tab(context)
            banks = eval_js(context, "_commitmentsData.filters.banks")
            options = eval_js(context, "document.querySelectorAll('#commitments-bank-filter option').length")
            bank = _bank_with_events(context)
        if not bank:
            step("Commitments Bank Filter", False, "no bank has any calendar event, even after creating test data")
        elif options != len(banks) + 1:
            step("Commitments Bank Filter", False, f"{options} dropdown options for {len(banks)} banks")
        else:
            _check_bank_filter(context, step, shot, bank)
    finally:
        if created:
            _api(context, "DELETE", f"/api/recurring-transactions/{created[1]}/")
            _api(context, "DELETE", f"/api/banks/{created[0]}/")
            open_tab(context)
