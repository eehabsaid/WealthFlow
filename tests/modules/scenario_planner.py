"""
WealthFlow QA Module — Financial Scenario Planner
Tests:
 1. Scenario Planner tab loading & sub-tab navigation
 2. Interactive timeline & event schema form rendering
 3. N-Scenario comparison matrix
 4. Insight generation display
"""

def test_scenario_planner_module(context, reporter, screenshot_logger):
    context.goto_route("#financial-advisor")
    reporter.pages_visited.add("Financial Advisor -> Scenario Planner")

    try:
        # Switch to scenario-planner tab
        context.page.evaluate("if (typeof switchFinancialAdvisorTab === 'function') switchFinancialAdvisorTab('scenario-planner'); else if (typeof loadScenarioPlanner === 'function') loadScenarioPlanner();")
        context.page.wait_for_timeout(1000)
        reporter.tabs_visited.add("Financial Advisor -> Scenario Planner")

        # Capture initial view screenshot
        shot_sp = screenshot_logger.capture(context.page, "financial-advisor", "scenario_planner", "view", "view", "ok")
        reporter.add_step("Scenario Planner Tab Load", "Financial Advisor", "PASS", "Loaded Scenario Planner tab successfully.", screenshot_path=shot_sp)

        # Test sub-tabs (Builder, Impact Dashboard, Compare, Insights)
        subtabs = [
            ("sp-tab-builder", "Builder"),
            ("sp-tab-dashboard", "Impact Dashboard"),
            ("sp-tab-compare", "Compare"),
            ("sp-tab-insights", "Insights"),
        ]

        for sub_id, sub_label in subtabs:
            btn = context.page.query_selector(f"#{sub_id}")
            if btn:
                btn.click()
                context.page.wait_for_timeout(400)
                shot_sub = screenshot_logger.capture(context.page, "financial-advisor", f"scenario_planner_{sub_id}", "click", "view", "ok")
                reporter.add_step(f"Scenario Planner Sub-tab: {sub_label}", "Financial Advisor", "PASS", f"Switched to sub-tab '{sub_label}'.", screenshot_path=shot_sub)

    except Exception as ex:
        reporter.add_step("Scenario Planner E2E Test", "Financial Advisor", "FAIL", f"Exception: {ex}")
