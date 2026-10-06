"""
WealthFlow QA Module — Settings & Administration
Tests:
 1. 17-step CRUD on Banks (showBankModal), Currencies (showCurrencyModal), Gold Types (showGoldTypeModal), Gold Purities (showGoldPurityModal), and Users (showUserModal).
 2. Portable Backup Archive creation & download (triggerDownloadBackup() -> wealthflow_backup_*.wfbackup).
 3. Documentation Engine generation (handleGenerateClick()).
 4. AI Advisor "Instant Data Answers" toggle round-trip + instant-answer engine check (API-verified).
 5. Per-user "My AI Settings" tab + sysadmin monthly token limits panel (API-verified).

Split into one file per phase (200-line rule):
  - common.py            — shared _uid() helper
  - banks.py             — Phase 1: Bank Setting CRUD
  - currencies.py        — Phase 2: Currency Setting CRUD
  - gold_types.py        — Phase 3: Gold Type Setting soft-toggle CRUD
  - gold_purities.py     — Phase 4: Gold Purity Setting soft-toggle CRUD
  - users.py             — Phase 5: User Account CRUD
  - backup_and_docs.py   — Phase 6: Backup Archive download & Documentation Engine trigger
  - ai_instant_answers.py — Phase 7: AI Advisor Instant Data Answers toggle + engine check
  - ai_user_settings.py   — Phase 8: My AI Settings tab + sysadmin token limits panel

This module re-exports test_settings_module, the entry point imported by
scripts/test_ui_human_full_e2e.py.
"""

from tests.modules.settings.banks import test_banks
from tests.modules.settings.currencies import test_currencies
from tests.modules.settings.gold_types import test_gold_types
from tests.modules.settings.gold_purities import test_gold_purities
from tests.modules.settings.users import test_users
from tests.modules.settings.common import open_settings_tab
from tests.modules.settings.backup_and_docs import test_backup_and_docs
from tests.modules.settings.ai_instant_answers import test_ai_instant_answers
from tests.modules.settings.ai_user_settings import test_ai_user_settings
from tests.modules.settings.legal_text import test_legal_text


def test_settings_module(context, reporter, screenshot_logger):

    context.goto_route("#settings")
    reporter.pages_visited.add("Settings & Administration")

    # Sweep sub-tabs
    # Every tab is a real route; a tab that does not open is a FAIL step, not a silent skip.
    tabs = ["languages", "banks", "currencies", "gold-settings", "email-templates", "backup", "documentation", "users", "legal"]
    for t in tabs:
        opened = open_settings_tab(context, t, wait_ms=700)
        if opened:
            reporter.tabs_visited.add(f"Settings -> {t}")
        shot = screenshot_logger.capture(context.page, "settings", f"tab_{t}", "none", "view", "ok" if opened else "fail")
        reporter.add_step(f"Settings tab opens: {t}", "Settings", "PASS" if opened else "FAIL",
                          f"hash={context.page.evaluate('location.hash')}", screenshot_path=shot)

    test_banks(context, reporter, screenshot_logger)
    test_currencies(context, reporter, screenshot_logger)
    test_gold_types(context, reporter, screenshot_logger)
    test_gold_purities(context, reporter, screenshot_logger)
    test_users(context, reporter, screenshot_logger)
    test_backup_and_docs(context, reporter, screenshot_logger)
    test_ai_instant_answers(context, reporter, screenshot_logger)
    test_ai_user_settings(context, reporter, screenshot_logger)
    test_legal_text(context, reporter, screenshot_logger)
