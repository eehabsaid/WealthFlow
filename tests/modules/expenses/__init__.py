"""
WealthFlow QA Module — Expenses & Reports
Tests:
 1. 17-step CRUD on Expense Categories (showCategoryModal), Subcategories (showSubcategoryModal), and Expense Records (showExpenseModal).
 2. CSV Export verification (exportExpenses() -> expenses_*.csv).
 3. Immediate downstream verification (Dashboard, Reports, Cash Flow, Spending Intelligence).

Split into one file per phase (200-line rule):
  - categories.py           — Phase 1: Expense Category CRUD
  - subcategories.py        — Phase 2: Expense Subcategory CRUD + category cleanup
  - records.py              — Phase 3: Expense Record CRUD
  - export_and_downstream.py — Phase 4: CSV Export + Phase 5: downstream verification

This module re-exports test_expenses_module, the entry point imported by
scripts/test_ui_human_full_e2e.py.
"""

from tests.core.data_generator import get_unique_expense_category_data
from tests.modules.expenses.categories import test_categories
from tests.modules.expenses.subcategories import test_subcategories
from tests.modules.expenses.records import test_records
from tests.modules.expenses.export_and_downstream import test_export_and_downstream


def test_expenses_module(context, reporter, screenshot_logger):
    context.goto_route("#expenses")
    reporter.pages_visited.add("Expenses & Reports")

    # Sweep tabs
    tabs = ["expenses-list", "expense-categories", "expense-subcategories", "reports-summary"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchTab === 'function') switchTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Expenses -> {t}")

    cat_data = get_unique_expense_category_data()

    category_id_for_subtest = test_categories(context, reporter, screenshot_logger, cat_data)
    test_subcategories(context, reporter, screenshot_logger, cat_data, category_id_for_subtest)
    test_records(context, reporter, screenshot_logger, cat_data)
    test_export_and_downstream(context, reporter, screenshot_logger)
