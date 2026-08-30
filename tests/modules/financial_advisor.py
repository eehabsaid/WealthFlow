"""
WealthFlow QA Module — Financial Advisor
Tests:
 1. Deep sweep of all 10 Financial Advisor sub-tabs:
    - Overview
    - Cash Flow Forecast
    - Wealth Growth Forecast
    - Portfolio Optimizer
    - Goal Planning
    - Risk Analysis
    - Spending Intelligence
    - Opportunity Detection
    - Performance Analytics
    - What-If Simulator
 2. 17-step CRUD on Financial Goals.
 3. Interactive controls testing (What-If Salary & Expense sliders).
"""

from tests.core.data_generator import get_unique_goal_data
from tests.core.crud_verifier import CrudVerifier

def test_financial_advisor_module(context, reporter, screenshot_logger):
    # Registered persistently: goal delete uses a native confirm() dialog.
    context.page.on("dialog", lambda dialog: dialog.accept())

    context.goto_route("#financial-advisor")
    reporter.pages_visited.add("Financial Advisor")

    fa_tabs = [
        ("overview", "Overview Dashboard"),
        ("cash-flow-forecast", "Cash Flow Forecast"),
        ("wealth-growth-forecast", "Wealth Growth Forecast"),
        ("portfolio-optimizer", "Portfolio Optimizer"),
        ("goal-planning", "Goal Planning"),
        ("risk-analysis", "Risk Analysis"),
        ("spending-intelligence", "Spending Intelligence"),
        ("opportunity-detection", "Opportunity Detection"),
        ("performance", "Performance Analytics"),
        ("what-if-simulator", "What-If Simulator"),
        ("scenario-planner", "Scenario Planner"),
    ]

    for tab_id, tab_label in fa_tabs:
        try:
            context.page.evaluate(f"if (typeof switchFinancialAdvisorTab === 'function') switchFinancialAdvisorTab('{tab_id}');")
            context.page.wait_for_timeout(700)
            reporter.tabs_visited.add(f"Financial Advisor -> {tab_label}")

            if tab_id == "what-if-simulator":
                # Interact with interactive sliders
                context.page.evaluate("""() => {
                    const s = document.getElementById('whatif-salary-slider');
                    if (s) { s.value = 25; s.dispatchEvent(new Event('input')); }
                    const e = document.getElementById('whatif-expenses-slider');
                    if (e) { e.value = -12; e.dispatchEvent(new Event('input')); }
                }""")
                context.page.wait_for_timeout(600)

            shot_tab = screenshot_logger.capture(context.page, "financial-advisor", tab_id, "none", "view", "ok")
            reporter.add_step(f"Financial Advisor Tab: {tab_label}", "Financial Advisor", "PASS", f"Swept tab '{tab_label}'.", screenshot_path=shot_tab)
        except Exception as ex:
            reporter.add_step(f"Financial Advisor Tab: {tab_label}", "Financial Advisor", "FAIL", f"Exception: {ex}")

    # Goal CRUD Test — real, API-verified. Save/edit/delete here are wired
    # via addEventListener on real buttons reading a hidden #goalIdInput,
    # not exposed as global functions — clicking real elements throughout,
    # including the goal card's data-goal-action buttons for edit/delete.
    goal_data = get_unique_goal_data()
    goal_checker = CrudVerifier(context.page, api_list_url="/api/goals/", list_key="goals")
    try:
        context.page.evaluate("if (typeof switchFinancialAdvisorTab === 'function') switchFinancialAdvisorTab('goal-planning');")
        context.page.wait_for_timeout(500)

        before_ids = goal_checker.snapshot_ids()

        add_btn = context.page.query_selector("#btnAddGoal, #btnAddGoalHeader, #btnAddGoalEmpty")
        if add_btn:
            add_btn.click()
        else:
            context.page.evaluate("""() => {
                const modalEl = document.getElementById('goalEditorModal');
                if (modalEl && window.bootstrap) { new bootstrap.Modal(modalEl).show(); }
            }""")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Financial Goal Modal")
        shot_goal = screenshot_logger.capture(context.page, "financial-advisor", "goal_modal", "openGoalModal", "open", "ok")
        goal_checker.add_manual_step(context.page.query_selector("#goalNameInput") is not None)

        if context.page.query_selector("#goalNameInput"):
            context.page.fill("#goalNameInput", goal_data["title"])
            context.page.fill("#goalTypeInput", "Savings")
            context.page.fill("#goalTargetAmountInput", str(goal_data["target_amount"]))
            if context.page.query_selector("#goalSavedAmountInput"):
                context.page.fill("#goalSavedAmountInput", "0")
            save_btn = context.page.query_selector("#btnSaveGoal")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(900)

        create_result = goal_checker.verify_created(before_ids, match_field="name", expected_value=goal_data["title"])

        new_title = goal_data["title"] + " Edited"
        if create_result.new_id is not None:
            edit_btn = context.page.query_selector(f'[data-goal-action="edit"][data-goal-id="{create_result.new_id}"]')
            if edit_btn:
                edit_btn.click()
                context.page.wait_for_timeout(600)
                if context.page.query_selector("#goalNameInput"):
                    context.page.fill("#goalNameInput", new_title)
                    save_btn = context.page.query_selector("#btnSaveGoal")
                    if save_btn:
                        save_btn.click()
                        context.page.wait_for_timeout(900)
        edit_result = goal_checker.verify_field_updated(create_result.new_id, "name", new_title)

        if create_result.new_id is not None:
            delete_btn = context.page.query_selector(f'[data-goal-action="delete"][data-goal-id="{create_result.new_id}"]')
            if delete_btn:
                delete_btn.click()
                context.page.wait_for_timeout(900)
        delete_result = goal_checker.verify_deleted(create_result.new_id)

        overall_pass = create_result.passed and edit_result.passed and delete_result.passed
        reporter.record_crud("Financial Goal", goal_checker.steps_passed, goal_checker.steps_total)
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
        reporter.add_step("Financial Goal CRUD (API-verified)", "Financial Advisor", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot_goal)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "financial-advisor", "goal_modal", "error", "fail", "fail")
        reporter.record_crud("Financial Goal", goal_checker.steps_passed, max(goal_checker.steps_total, 1))
        reporter.add_step("Financial Goal CRUD Test", "Financial Advisor", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)
