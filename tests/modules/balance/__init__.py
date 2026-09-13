"""
WealthFlow QA Module — Balance & Net Worth
Tests:
 1. Full 17-step CRUD on Balance Accounts & Add/Edit Balance Entry Modal.
 2. Full 17-step CRUD on Balance Transfers & Transfer Modal (showTransferModal).
 3. Immediate downstream cross-module verification (Dashboard Net Worth & Advisor Overview).

Split into one file per phase (200-line rule):
  - accounts.py            — Phase 1: Balance Account CRUD + downstream verification
  - transfers.py           — Phase 2: Balance Transfer CRUD
  - currency_exchange.py   — Phase 3: Currency Exchange structural check
  - bank_interest.py       — Phase 4: Bank Interest CRUD
  - credit_card_payment.py — Phase 5: Credit Card Payment CRUD
  - card_renewal_fee.py    — Phase 6: Card Renewal Fee CRUD

This module re-exports test_balance_module, the entry point imported by
scripts/test_ui_human_full_e2e.py.
"""

from tests.modules.balance.accounts import test_accounts
from tests.modules.balance.transfers import test_transfers
from tests.modules.balance.currency_exchange import test_currency_exchange
from tests.modules.balance.bank_interest import test_bank_interest
from tests.modules.balance.credit_card_payment import test_credit_card_payment
from tests.modules.balance.card_renewal_fee import test_card_renewal_fee


def test_balance_module(context, reporter, screenshot_logger):
    # Registered once, persistently, for the whole module: several delete
    # actions below trigger a native confirm() dialog. Playwright
    # auto-dismisses (returns false) any dialog with no handler attached,
    # and attaching one right before the triggering call can race with a
    # dialog fired synchronously from inside page.evaluate() — registering
    # early avoids that.
    context.page.on("dialog", lambda dialog: dialog.accept())

    context.goto_route("#balance")
    reporter.pages_visited.add("Balance & Net Worth")

    # Sweep sub-tabs
    tabs = ["accounts", "transfers", "currency_exchange", "bank_interest", "credit_card_payment", "card_renewal_fee"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchTab === 'function') switchTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Balance -> {t}")

    test_accounts(context, reporter, screenshot_logger)
    test_transfers(context, reporter, screenshot_logger)
    test_currency_exchange(context, reporter, screenshot_logger)
    test_bank_interest(context, reporter, screenshot_logger)
    test_credit_card_payment(context, reporter, screenshot_logger)
    test_card_renewal_fee(context, reporter, screenshot_logger)
