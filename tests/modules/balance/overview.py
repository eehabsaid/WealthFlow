"""Balance module phase 0: Overview tab shows only currencies with a positive amount.

Drives the real renderBalanceOverview() in the live page with synthetic totals
(no data is written), so the three cases are deterministic on any database:
  1. a zero-amount currency gives no card,
  2. a positive amount gives a card,
  3. when every amount is zero the friendly empty state replaces the cards.
"""

_RENDER_JS = """(mode) => {
  const cur = (typeof _currencies !== 'undefined' && _currencies.length) ? _currencies : [];
  if (cur.length < 2) return {skip: true, count: cur.length};
  const totals = {};
  cur.forEach((c) => { totals[c.code] = 0; });
  if (mode === 'mixed') totals[cur[1].code] = 125.5;
  renderBalanceOverview({
    totals, terms: [], foreignValue: 0, goldValue: 0, grandTotal: 0, netWorth: 0,
    cashBase: 0, forecastData: {}, formulaDesc: '', grandTotalLabel: '',
  });
  const pane = document.getElementById('bal-pane-overview');
  return {
    skip: false,
    cards: [...pane.querySelectorAll('.currency-card .cur-code')].map((e) => e.textContent.trim()),
    empty: !!pane.querySelector('#balOverviewEmpty'),
    zeroCode: cur[0].code,
    positiveCode: cur[1].code,
  };
}"""


def test_overview(context, reporter, screenshot_logger):
    try:
        context.goto_route("#balance")
        context.page.evaluate("if (typeof switchTab === 'function') switchTab('overview');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add("Balance -> overview")

        mixed = context.page.evaluate(_RENDER_JS, "mixed")
        if mixed.get("skip"):
            reporter.add_step("Balance Overview hides zero-amount currencies", "Balance & Net Worth", "SKIP",
                              f"Needs at least 2 currencies, found {mixed.get('count')}.")
            return
        shot_mixed = screenshot_logger.capture(context.page, "balance", "overview", "none", "zero_hidden", "ok")
        ok_zero = mixed["zeroCode"] not in mixed["cards"]
        ok_positive = mixed["cards"] == [mixed["positiveCode"]] and not mixed["empty"]

        all_zero = context.page.evaluate(_RENDER_JS, "zero")
        shot_empty = screenshot_logger.capture(context.page, "balance", "overview", "none", "empty_state", "ok")
        ok_empty = all_zero["cards"] == [] and all_zero["empty"]

        for label, ok, shot in (
            ("Balance Overview: zero-amount currency gives no card", ok_zero, shot_mixed),
            ("Balance Overview: positive amount gives a card", ok_positive, shot_mixed),
            ("Balance Overview: all-zero shows the empty state", ok_empty, shot_empty),
        ):
            reporter.add_step(label, "Balance & Net Worth", "PASS" if ok else "FAIL",
                              f"mixed={mixed['cards']} empty={mixed['empty']}; all_zero={all_zero['cards']} empty={all_zero['empty']}",
                              screenshot_path=shot)
        context.goto_route("#balance")  # restore the real data render
    except Exception as ex:
        reporter.add_step("Balance Overview Test", "Balance & Net Worth", "FAIL", f"Exception: {ex}")
