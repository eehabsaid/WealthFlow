"""Commitments Calendar E2E: month/week/agenda never overflow on phones (375x812, 414x896), columns equal, day detail opens."""

from tests.modules.commitments_calendar_support import click, eval_js

VIEWPORTS = ((375, 812), (414, 896))

# Several events on one day (+ one on the 1st and the last day of the grid) so chips, bars and "+N" all render.
_INJECT = """() => {
  const first = new Date(_commitmentsAnchor.getFullYear(), _commitmentsAnchor.getMonth(), 1);
  const iso = (n) => _commitmentsLocalISO(new Date(first.getFullYear(), first.getMonth(), n));
  const mk = (n, cat, k) => ({date: iso(n), category: cat, source: 'RecurringTransaction', description_key: 'commitments_source_recurring',
    amount: 100 + k, amount_base: 100 + k, currency_code: 'EGP', extra: {name: 'A very long commitment name number ' + k}});
  window.__cmtBackup = _commitmentsData.events;
  _commitmentsData.events = [mk(10, 'expense', 1), mk(10, 'income', 2), mk(10, 'renewal', 3), mk(10, 'expense', 4), mk(10, 'expense', 5),
    mk(1, 'expense', 6), mk(28, 'income', 7)];
  _refreshCommitmentsView();
}"""

_MEASURE = """() => {
  const cells = Array.from(document.querySelectorAll('.commitments-day-cell'));
  const heads = Array.from(document.querySelectorAll('.commitments-weekday'));
  const vw = document.documentElement.clientWidth;
  const row = cells.slice(0, 7).map(c => c.getBoundingClientRect());
  const widths = row.map(r => r.width);
  const card = document.querySelector('#commitments-view .commitments-card');
  const sat = row[6];
  const hdrOff = heads.map((h, i) => Math.abs(h.getBoundingClientRect().left - row[i].left));
  return {widths, equal: Math.max(...widths) - Math.min(...widths) <= 1,
          cardFits: card.scrollWidth <= card.clientWidth && document.documentElement.scrollWidth <= vw,
          lastInside: sat.left >= -0.5 && sat.right <= vw + 0.5,
          headerAligned: heads.length === 7 && hdrOff.every(o => o <= 1),
          rtl: document.documentElement.dir || getComputedStyle(document.body).direction};
}"""

_OVERFLOW = """() => {
  const card = document.querySelector('#commitments-view .card');
  return card ? {fits: card.scrollWidth <= card.clientWidth && document.documentElement.scrollWidth <= document.documentElement.clientWidth,
                 sw: card.scrollWidth, cw: card.clientWidth} : {fits: false};
}"""


def run_mobile_layout(context, step, shot):
    page = context.page
    original_size = page.viewport_size
    eval_js(context, _INJECT)
    try:
        for width, height in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": height})
            click(context, '[data-commitments-view="month"]', 500)
            m = eval_js(context, _MEASURE)
            tag = f"{width}px"
            step(f"Commitments Mobile Month Equal Columns ({tag})", m["equal"], f"widths={[round(w, 1) for w in m['widths']]}" if not m["equal"] else "7 equal columns (+-1px).")
            step(f"Commitments Mobile Month No Horizontal Overflow ({tag})", m["cardFits"], "Card and page do not scroll sideways." if m["cardFits"] else str(m))
            step(f"Commitments Mobile Last Column Inside Viewport ({tag})", m["lastInside"], f"Last column fully visible (dir={m['rtl']}).")
            step(f"Commitments Mobile Weekday Headers Aligned ({tag})", m["headerAligned"], "Headers line up with day cells.")
            day = eval_js(context, "_commitmentsLocalISO(new Date(_commitmentsAnchor.getFullYear(), _commitmentsAnchor.getMonth(), 10))")
            page.evaluate("document.getElementById('commitments-day-detail').innerHTML = ''")
            page.locator(f'[data-commitments-day="{day}"]').first.click()
            page.wait_for_timeout(300)
            cards = page.locator("#commitments-day-detail .commitments-event-card").count()
            step(f"Commitments Mobile Tap Opens Day Detail ({tag})", cards == 5, f"{cards} event cards shown (expected 5).",
                 shot("commitments_calendar_mobile", f"month_{width}"))
            for view in ("week", "agenda"):
                click(context, f'[data-commitments-view="{view}"]', 500)
                o = eval_js(context, _OVERFLOW)
                step(f"Commitments Mobile {view.title()} View No Overflow ({tag})", o["fits"], str(o))
    finally:
        if original_size:
            page.set_viewport_size(original_size)
        page.evaluate("() => { _commitmentsData.events = window.__cmtBackup; _refreshCommitmentsView(); }")
        click(context, '[data-commitments-view="month"]', 500)
