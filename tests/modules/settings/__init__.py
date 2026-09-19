"""
WealthFlow QA Module — Settings & Administration
Tests:
 1. 17-step CRUD on Banks (showBankModal), Currencies (showCurrencyModal), Gold Types (showGoldTypeModal), Gold Purities (showGoldPurityModal), and Users (showUserModal).
 2. Portable Backup Archive creation & download (triggerDownloadBackup() -> wealthflow_backup_*.wfbackup).
 3. Documentation Engine generation (handleGenerateClick()).

Split into one file per phase (200-line rule):
  - common.py            — shared _uid() helper
  - banks.py             — Phase 1: Bank Setting CRUD
  - currencies.py        — Phase 2: Currency Setting CRUD
  - gold_types.py        — Phase 3: Gold Type Setting soft-toggle CRUD
  - gold_purities.py     — Phase 4: Gold Purity Setting soft-toggle CRUD
  - users.py             — Phase 5: User Account CRUD
  - backup_and_docs.py   — Phase 6: Backup Archive download & Documentation Engine trigger

This module re-exports test_settings_module, the entry point imported by
scripts/test_ui_human_full_e2e.py.
"""

from tests.modules.settings.banks import test_banks
from tests.modules.settings.currencies import test_currencies
from tests.modules.settings.gold_types import test_gold_types
from tests.modules.settings.gold_purities import test_gold_purities
from tests.modules.settings.users import test_users
from tests.modules.settings.backup_and_docs import test_backup_and_docs


def test_settings_module(context, reporter, screenshot_logger):

    context.goto_route("#settings")
    reporter.pages_visited.add("Settings & Administration")

    # Sweep sub-tabs
    tabs = ["general", "banks", "currencies", "gold-settings", "email-templates", "backup", "documentation", "users"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchSettingsTab === 'function') switchSettingsTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Settings -> {t}")

    test_banks(context, reporter, screenshot_logger)
    test_currencies(context, reporter, screenshot_logger)
    test_gold_types(context, reporter, screenshot_logger)
    test_gold_purities(context, reporter, screenshot_logger)
    test_users(context, reporter, screenshot_logger)
    test_backup_and_docs(context, reporter, screenshot_logger)
