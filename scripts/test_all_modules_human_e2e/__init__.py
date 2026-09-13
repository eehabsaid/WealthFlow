"""Entry point for scripts/test_all_modules_human_e2e/, split by phase
(200-line rule):
  - currency_exchange.py       — Phase 1: Currency Exchange E2E test
  - per_diem.py                — Phase 2: Per Diem / Salary E2E test
  - expenses.py                — Phase 3: Expenses E2E test
  - net_worth_fixed_assets.py  — Phase 4: Net Worth & Fixed Assets E2E test
  - ui_sweep.py                — Phase 5: UI Playwright Human Experience sweep

Phases share state (accounts, exchange, expense, etc. created in one
phase and consumed/cleaned up in a later one) via a SimpleNamespace
context object passed between them.
"""

import sys
import os
from decimal import Decimal
from types import SimpleNamespace

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)
os.environ['DJANGO_SETTINGS_MODULE'] = 'wealthflow.settings'

import django
django.setup()

from django.contrib.auth.models import User
from core.models import Currency, ExchangeRate, CurrencyExchange

from scripts.test_all_modules_human_e2e.currency_exchange import run_currency_exchange_test
from scripts.test_all_modules_human_e2e.per_diem import run_per_diem_test
from scripts.test_all_modules_human_e2e.expenses import run_expenses_test
from scripts.test_all_modules_human_e2e.net_worth_fixed_assets import run_net_worth_fixed_assets_test
from scripts.test_all_modules_human_e2e.ui_sweep import run_ui_sweep


def run_all_modules_human_e2e_tests():
    print("\n==================================================================")
    print("  WEALTHFLOW COMPREHENSIVE E2E HUMAN QA SUITE                     ")
    print("  Modules: Currency Exchange, Per Diem, Expenses, Net Worth & FA  ")
    print("==================================================================")

    ctx = SimpleNamespace()
    ctx.user = User.objects.first() or User.objects.create_user(username="qa_human_user", password="password")

    # Setup Currencies & Rates
    ctx.egp = Currency.objects.get(code="EGP")
    ctx.usd = Currency.objects.get(code="USD")

    ExchangeRate.objects.filter(currency_code="USD").delete()
    ctx.rate_usd = ExchangeRate.objects.create(
        currency_code="USD",
        currency_name="US Dollar",
        buy_rate=Decimal("50.000000"),
        sell_rate=Decimal("50.500000"),
        mid_rate=Decimal("50.250000"),
        source="QA_Test"
    )

    run_currency_exchange_test(ctx)
    run_per_diem_test(ctx)
    run_expenses_test(ctx)
    run_net_worth_fixed_assets_test(ctx)
    run_ui_sweep()

    # Clean up test rows
    CurrencyExchange.objects.all().delete()
    ctx.ce.delete()
    ctx.pd.delete()
    ctx.exp.delete()
    ctx.bal_egp.delete()
    ctx.bal_usd.delete()
    ctx.company.delete()
    ctx.cat.delete()
    ctx.rate_usd.delete()

    print("\n==================================================================")
    print("  ALL 5 MODULE E2E HUMAN QA SCENARIOS PASSED WITH ZERO ERRORS     ")
    print("==================================================================")


if __name__ == "__main__":
    run_all_modules_human_e2e_tests()
