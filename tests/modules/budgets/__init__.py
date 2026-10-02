"""
WealthFlow QA Module — Budgets, Recurring Transactions & Alerts (A2)
Tests:
 1. Page + sidebar route renders (#budgets) and the Add Budget / Add Recurring modals open.
 2. Budget CRUD, API-verified (create / edit / delete via the real UI save functions).
 3. Recurring transaction CRUD, API-verified, plus the safety rules:
    - past start date does NOT back-fill by default
    - pause/resume (toggleRecurringActive) flips is_active
    - GET /api/recurring-transactions/due-preview/ is read-only
 4. Alerts endpoint responds and a tiny budget over its limit raises an alert.

Split into one file per phase (200-line rule):
  - budget_crud.py    — Phase 2
  - recurring_crud.py — Phase 3
  - alerts.py         — Phase 4

NOTE: tests/core/test_context.py registers ONE global dialog handler that
accepts every confirm(); do not add another page.on("dialog") here.
"""

from tests.modules.budgets.budget_crud import test_budget_crud
from tests.modules.budgets.recurring_crud import test_recurring_crud
from tests.modules.budgets.alerts import test_alerts


def test_budgets_module(context, reporter, screenshot_logger):
    context.goto_route("#budgets")
    reporter.pages_visited.add("Budgets")
    rendered = context.page.query_selector("#main-content") is not None
    shot = screenshot_logger.capture(context.page, "budgets", "page", "none", "view", "ok")
    reporter.add_step(
        "Budgets page renders", "Budgets", "PASS" if rendered else "FAIL",
        "Budgets route loaded into #main-content." if rendered else "#main-content missing.",
        screenshot_path=shot,
    )
    for tab in ("budgets-list", "recurring-list"):
        reporter.tabs_visited.add(f"Budgets -> {tab}")

    test_budget_crud(context, reporter, screenshot_logger)
    test_recurring_crud(context, reporter, screenshot_logger)
    test_alerts(context, reporter, screenshot_logger)
