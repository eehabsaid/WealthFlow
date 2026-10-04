"""Gulf module phase: every Financial Advisor tab must be free of EGP for a SAR/AED-base user."""

ADVISOR_TABS = [
    "overview", "cash-flow-forecast", "wealth-growth-forecast", "portfolio-optimizer", "goal-planning",
    "risk-analysis", "spending-intelligence", "opportunity-detection", "performance", "what-if-simulator",
    "scenario-planner",
]


def check_advisor_no_egp(context, reporter, screenshot_logger, code):
    page = context.page
    context.goto_route("#financial-advisor")
    page.wait_for_timeout(900)
    offenders = {}
    not_swept = []  # a tab that never opened (or showed nothing) must fail, not pass vacuously
    for tab in ADVISOR_TABS:
        page.evaluate(f"if (typeof switchFinancialAdvisorTab === 'function') switchFinancialAdvisorTab('{tab}');")
        page.wait_for_timeout(900)
        text = page.inner_text("#main-content") if page.query_selector("#main-content") else ""
        opened = page.evaluate(f"!!document.querySelector('#fa-tab-{tab}.active')")
        if not opened or len(text.strip()) < 50:
            not_swept.append(tab)
        if "EGP" in text or "ج.م" in text:
            offenders[tab] = text[max(0, text.find("EGP") - 40):text.find("EGP") + 40].replace("\n", " ")
        if tab == "performance":
            _check_performance_gold(page, reporter, screenshot_logger, code)
    ok = not offenders and not not_swept
    shot = screenshot_logger.capture(page, "gulf_market", f"{code.lower()}_advisor", "none", "view", "ok" if ok else "fail")
    reporter.add_step(f"[{code}] Financial Advisor tabs show no EGP", "Gulf Markets", "PASS" if ok else "FAIL",
                      f"tabs_swept={len(ADVISOR_TABS) - len(not_swept)}/{len(ADVISOR_TABS)} not_opened={not_swept} offenders={offenders}", screenshot_path=shot)


def _check_performance_gold(page, reporter, screenshot_logger, code):
    gold = page.evaluate("fetch('/api/financial-advisor/performance/').then(r => r.json()).then(d => d.gold)")
    has_data = bool(gold and gold.get("timeseries"))
    ok = (not has_data) or (gold.get("currency") == code and gold.get("market") == "spot")
    shot = screenshot_logger.capture(page, "gulf_market", f"{code.lower()}_performance_gold", "none", "view", "ok" if ok else "fail")
    reporter.add_step(f"[{code}] Performance gold history is spot in {code}", "Gulf Markets", "PASS" if ok else "FAIL",
                      f"currency={(gold or {}).get('currency')} market={(gold or {}).get('market')} rows={len((gold or {}).get('timeseries', []))}",
                      screenshot_path=shot)
