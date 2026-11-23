"""Commitments Calendar E2E: today's box is highlighted (month cell and week column), exactly one, on the right date."""

from tests.modules.commitments_calendar_support import click, eval_js

_CHECK = """(sel) => {
  const iso = _commitmentsLocalISO(new Date());
  const marked = Array.from(document.querySelectorAll(sel + '.commitments-today'));
  const plain = Array.from(document.querySelectorAll(sel + ':not(.commitments-today)'));
  const style = (el) => { const c = getComputedStyle(el); return c.backgroundColor + '|' + c.borderTopColor; };
  const day = (el) => el.dataset.commitmentsDay || el.dataset.commitmentsWeekDay;
  return {count: marked.length, day: marked[0] ? day(marked[0]) : null, iso,
          current: marked[0] ? marked[0].getAttribute('aria-current') : null,
          differs: marked[0] ? plain.every(p => style(p) !== style(marked[0])) : false};
}"""


def run_today_highlight(context, step, shot):
    results = {}
    for view, sel in (("month", ".commitments-day-cell"), ("week", ".commitments-week-day")):
        click(context, f'[data-commitments-view="{view}"]', 600)
        click(context, "[data-commitments-today]", 600)
        results[view] = eval_js(context, f"({_CHECK})('{sel}')")
    click(context, '[data-commitments-view="month"]', 500)
    ok = all(r["count"] == 1 and r["day"] == r["iso"] and r["current"] == "date" and r["differs"] for r in results.values())
    step("Commitments Today Box Highlighted", ok,
         f"Month and week views each highlight exactly one box ({results['month']['iso']}) in a colour no other box has."
         if ok else str(results), shot("commitments_calendar_today", "today"))
