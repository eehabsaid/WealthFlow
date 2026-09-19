"""
WealthFlow QA Module — Employment & Salary
Tests:
 1. 17-step CRUD on Companies (showCompanyModal), Salary Entries (showSalaryModal), and Per Diems (showPerDiemFormModal).
 2. Excel Workbook export download verification (/api/export/excel/ -> Balance_Tracker_*.xlsx).
 3. Immediate cross-module downstream impact assertions.

Split into one file per phase (200-line rule):
  - company.py               — Phase 1: Company CRUD
  - salary_entry.py          — Phase 2: Salary Entry CRUD
  - per_diem.py              — Phase 3: Per Diem CRUD + company cleanup
  - export_and_downstream.py — Phase 4: Excel Download + Phase 5: downstream verification

This module re-exports test_salary_module, the entry point imported by
scripts/test_ui_human_full_e2e.py.
"""

from tests.core.data_generator import get_unique_company_data
from tests.modules.salary.company import test_company
from tests.modules.salary.salary_entry import test_salary_entry
from tests.modules.salary.per_diem import test_per_diem
from tests.modules.salary.export_and_downstream import test_export_and_downstream


def test_salary_module(context, reporter, screenshot_logger):
    context.goto_route("#employment")
    reporter.pages_visited.add("Employment & Salary")

    # Sweep tabs
    tabs = ["dashboard", "salary-list", "per-diem", "companies"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchTab === 'function') switchTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Salary -> {t}")

    comp_data = get_unique_company_data()
    test_year = 2026

    company_id = test_company(context, reporter, screenshot_logger, comp_data)
    test_salary_entry(context, reporter, screenshot_logger, company_id, test_year)
    test_per_diem(context, reporter, screenshot_logger, company_id, test_year)
    test_export_and_downstream(context, reporter, screenshot_logger)
