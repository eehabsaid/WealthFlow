"""
WealthFlow QA Module — Design system (tokens, money formatting, chart contrast).
Checks in the real browser, in BOTH themes, on Dashboard / Balance / Financial Advisor:
 1. Semantic + chart tokens resolve to real colours.
 2. Money figures use tabular numerals.
 3. Balance and Advisor money KPIs show exactly 2 decimals (rates/percentages are exempt).
 4. A near-black data colour stays visible on dark and a near-white one on light.
 5. Dashboard panels use the shared surface-panel and the page has no horizontal overflow on mobile width.
NOTE: tests/core/test_context.py registers ONE global dialog handler; do not add another page.on("dialog") here.
"""

import re

TOKENS_JS = """() => {
    const s = getComputedStyle(document.documentElement);
    const names = ['--positive', '--negative', '--warning', '--info', '--focus-ring-color', '--chart-grid']
        .concat([1, 2, 3, 4, 5, 6, 7, 8].map((i) => '--chart-' + i));
    return names.filter((n) => !s.getPropertyValue(n).trim());
}"""

CONTRAST_JS = """() => {
    const dark = readableChartColor('#000000');
    const light = readableChartColor('#ffffff');
    return {theme: document.documentElement.getAttribute('data-theme'), dark, light,
            sameHue: readableChartColor('#10b981') !== ''};
}"""

MONEY_RE = re.compile(r"^-?[\d,\u066c\u066b\u0660-\u0669.]+\.\d{2}$|^-?[\d,]+$")


def _step(reporter, shots, page, name, ok, detail, tab="check"):
    shot = shots.capture(page, "design_system", tab, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "Design System", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _set_theme(page, theme):
    """Use the app's own toggle (the shared set_theme helper only sets data-bs-theme, never data-theme)."""
    page.evaluate(
        "(th) => { if ((th === 'light') !== isLightTheme()) toggleTheme(); }",
        theme,
    )
    page.wait_for_timeout(600)


def _lum(hex_color):
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _check_theme(context, reporter, shots, theme):
    page = context.page
    context.goto_route("#dashboard")
    _set_theme(page, theme)  # after navigation: a reload would reset the theme
    page.wait_for_timeout(1500)
    missing = page.evaluate(TOKENS_JS)
    _step(reporter, shots, page, f"Design tokens resolve ({theme})", not missing, f"missing={missing}", f"tokens_{theme}")

    tab = page.evaluate("() => getComputedStyle(document.querySelector('.kpi-value')).fontVariantNumeric")
    _step(reporter, shots, page, f"KPI values use tabular numerals ({theme})", "tabular-nums" in tab, f"font-variant-numeric={tab}", f"numerals_{theme}")

    c = page.evaluate(CONTRAST_JS)
    ok = c["theme"] == theme and ((_lum(c["dark"]) >= 0.12) if theme == "dark" else (_lum(c["light"]) <= 0.7))
    _step(reporter, shots, page, f"Near-invisible data colours are lifted ({theme})", ok, str(c), f"contrast_{theme}")

    panels = len(page.query_selector_all(".surface-panel"))
    _step(reporter, shots, page, f"Dashboard uses shared surface panels ({theme})", panels >= 2, f"surface-panel count={panels}", f"panels_{theme}")


def _check_money(context, reporter, shots):
    page = context.page
    _set_theme(page, "dark")
    context.goto_route("#balance")
    page.wait_for_timeout(2500)
    texts = page.eval_on_selector_all(
        "#bal-pane-overview .num-fmtmoney",
        "els => els.map(e => e.childNodes[0] ? e.childNodes[0].textContent.trim() : e.textContent.trim())",
    )
    bad = [t for t in texts if not re.search(r"[.\u066b]\d{2}$", t)]
    _step(reporter, shots, page, "Balance money KPIs show exactly 2 decimals", bool(texts) and not bad, f"checked={len(texts)} bad={bad}", "balance_money")

    context.goto_route("#financial-advisor")
    # Re-entering the Advisor restores the last-used tab (e.g. Goal Planning after the advisor CRUD
    # module) and does not render Overview until it is selected. Select it explicitly first.
    page.evaluate("() => { if (typeof switchFinancialAdvisorTab === 'function') switchFinancialAdvisorTab('overview'); }")
    try:
        page.wait_for_selector(".overview-kpi-value", state="attached", timeout=10000)
    except Exception:
        pass  # reported below as checked=0
    page.wait_for_timeout(800)
    adv = page.eval_on_selector_all(".overview-kpi-value", "els => els.map(e => e.textContent.trim())")
    bad = [t for t in adv if re.search(r"\d[.\u066b]\d{3,}", t)]
    _step(reporter, shots, page, "Advisor KPI values never show more than 2 decimals", bool(adv) and not bad, f"checked={len(adv)} bad={bad}", "advisor_money")


def _check_mobile_overflow(context, reporter, shots):
    page = context.page
    page.set_viewport_size({"width": 390, "height": 844})
    try:
        for route in ("#dashboard", "#balance", "#financial-advisor"):
            context.goto_route(route)
            page.wait_for_timeout(1800)
            over = page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            _step(reporter, shots, page, f"No horizontal overflow on mobile {route}", over <= 1, f"overflow_px={over}", "mobile" + route.replace("#", "_"))
    finally:
        page.set_viewport_size({"width": 1440, "height": 900})


def test_design_system_module(context, reporter, screenshot_logger):
    reporter.pages_visited.add("Design System")
    try:
        for theme in ("dark", "light"):
            reporter.tabs_visited.add(f"Design System -> {theme}")
            _check_theme(context, reporter, screenshot_logger, theme)
        reporter.tabs_visited.add("Design System -> money")
        _check_money(context, reporter, screenshot_logger)
        reporter.tabs_visited.add("Design System -> mobile")
        _check_mobile_overflow(context, reporter, screenshot_logger)
    except Exception as ex:
        _step(reporter, screenshot_logger, context.page, "Design system module", False, f"Exception: {ex}", "error")
    finally:
        _set_theme(context.page, "dark")
