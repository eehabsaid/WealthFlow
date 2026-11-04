"""Entry point for scripts/test_all_modules_human_e2e/, split by phase
(200-line rule):
  - currency_exchange.py       — Phase 1: Currency Exchange E2E test
  - per_diem.py                — Phase 2: Per Diem / Salary E2E test
  - expenses.py                — Phase 3: Expenses E2E test
  - net_worth_fixed_assets.py  — Phase 4: Net Worth & Fixed Assets E2E test
  - ui_sweep.py                — Phase 5: UI Playwright Human Experience sweep
  - launcher.py                — one-command start: disposable DB copy, server, clean-up (used when run by hand)

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

if __name__ == "__main__" and os.environ.get("WEALTHFLOW_HUMAN_E2E_CHILD") != "1":
    # Started by hand: prepare everything itself (disposable database copy, server, clean-up) - see launcher.py
    import importlib.util

    _spec = importlib.util.spec_from_file_location("human_e2e_launcher", os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.py"))
    _launcher = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_launcher)   # loaded by path: importing the package would run the Django setup below
    sys.exit(_launcher.run())
os.environ['DJANGO_SETTINGS_MODULE'] = 'wealthflow.settings'

import django
django.setup()

from django.conf import settings as _settings

if os.path.abspath(str(_settings.DATABASES["default"]["NAME"])) == os.path.join(_REPO_ROOT, "db.sqlite3"):
    sys.exit(
        "Refusing to run on db.sqlite3 itself: this QA script writes test rows into the database. Start it with "
        "`python scripts/test_all_modules_human_e2e/__init__.py` (it prepares a disposable copy by itself)."
    )

from django.contrib.auth.models import User
from core.models import Currency, ExchangeRate

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
    ctx.egp = Currency.objects.get(owner=ctx.user, code="EGP")   # currencies are per user (unique per owner + code)
    ctx.usd = Currency.objects.get(owner=ctx.user, code="USD")

    # Existing USD rates are kept: the QA rate below is the newest row, so it is the one every service reads (latest first)
    ctx.rate_usd = ExchangeRate.objects.create(
        currency_code="USD",
        currency_name="US Dollar",
        buy_rate=Decimal("50.000000"),
        sell_rate=Decimal("50.500000"),
        mid_rate=Decimal("50.250000"),
        source="QA_Test"
    )

    try:
        run_currency_exchange_test(ctx)
        run_per_diem_test(ctx)
        run_expenses_test(ctx)
        run_net_worth_fixed_assets_test(ctx)
        run_ui_sweep()
    finally:
        # Clean up only the rows this script created (also when a phase failed half way)
        for name in ("ce", "pd", "exp", "bal_base", "bal_usd", "company", "cat", "rate_usd"):
            row = getattr(ctx, name, None)
            if row is not None and row.pk is not None:
                row.delete()

    print("\n==================================================================")
    print("  ALL 5 MODULE E2E HUMAN QA SCENARIOS PASSED WITH ZERO ERRORS     ")
    print("==================================================================")


if __name__ == "__main__":
    run_all_modules_human_e2e_tests()
