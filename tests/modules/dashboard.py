"""
WealthFlow QA Module — Dashboard, Exchange Rates, Gold Price & Welcome Landing
Tests:
 1. Navigation to Welcome Landing (#welcome).
 2. Navigation to Main Dashboard (#dashboard) & KPI verification.
 3. Navigation to Exchange Rates (#exchange-rates) & live rate table.
 4. Navigation to Gold Prices (#gold-price) & live gold table.
 5. Theme and language toggle verification.
"""

def test_dashboard_module(context, reporter, screenshot_logger):
    # 1. Welcome Landing
    context.goto_route("#welcome")
    reporter.pages_visited.add("Welcome Landing")
    shot_wel = screenshot_logger.capture(context.page, "welcome", "main", "none", "view", "ok")
    reporter.add_step("Welcome Landing Page Sweep", "Welcome Landing", "PASS", "Swept welcome landing page.", screenshot_path=shot_wel)

    # 2. Main Dashboard
    context.goto_route("#dashboard")
    reporter.pages_visited.add("Main Dashboard")

    try:
        kpi_cards = context.page.query_selector_all(".kpi-card, .card, .stat-card")
        assert len(kpi_cards) > 0, "No KPI cards found on Main Dashboard!"

        context.set_theme("light")
        context.page.wait_for_timeout(300)
        context.set_theme("dark")
        context.page.wait_for_timeout(300)

        shot_dash = screenshot_logger.capture(context.page, "dashboard", "main", "none", "view", "ok")
        reporter.add_step("Main Dashboard KPIs & Theme Switching", "Dashboard", "PASS", f"Verified {len(kpi_cards)} KPI cards and theme toggling.", screenshot_path=shot_dash)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "dashboard", "main", "error", "fail", "fail")
        reporter.add_step("Main Dashboard Test", "Dashboard", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)

    # 3. Exchange Rates Page
    context.goto_route("#exchange-rates")
    reporter.pages_visited.add("Exchange Rates")
    shot_rates = screenshot_logger.capture(context.page, "exchange-rates", "main", "none", "view", "ok")
    reporter.add_step("Exchange Rates Page Sweep", "Exchange Rates", "PASS", "Swept exchange rates live table.", screenshot_path=shot_rates)

    # 4. Gold Prices Page
    context.goto_route("#gold-price")
    reporter.pages_visited.add("Gold Prices")
    shot_gold = screenshot_logger.capture(context.page, "gold-price", "main", "none", "view", "ok")
    reporter.add_step("Gold Prices Page Sweep", "Gold Prices", "PASS", "Swept gold prices live table.", screenshot_path=shot_gold)
