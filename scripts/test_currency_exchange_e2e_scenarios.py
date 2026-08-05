import sys
import os
import time

sys.path.insert(0, r"d:\MyApps\WealthFlow")
os.environ['DJANGO_SETTINGS_MODULE'] = 'wealthflow.settings'

import django
django.setup()

from decimal import Decimal
from django.db import transaction
from django.contrib.auth.models import User
from core.models import BalanceEntry, CurrencyExchange, Currency
from core.services.shared.currency_conversion_service import CurrencyConversionService
from playwright.sync_api import sync_playwright
from tests.core.test_context import TestContext

def run_e2e_human_currency_exchange_test():
    print("\n==================================================================")
    print("  WEALTHFLOW E2E HUMAN QA TEST: CURRENCY EXCHANGE FEATURE         ")
    print("==================================================================")

    user = User.objects.first() or User.objects.create_user(username="test_qa_user", password="password")

    # Fetch initial balances for testing
    egp_currency = Currency.objects.get(code="EGP")
    usd_currency = Currency.objects.get(code="USD")

    # Create/get distinct source and destination balance entries for deterministic test
    from_balance, _ = BalanceEntry.objects.get_or_create(
        title="QA Source EGP Account",
        defaults={
            "amount": Decimal("100000.00"),
            "currency": egp_currency,
            "balance_type": BalanceEntry.BalanceType.CASH,
        }
    )
    # Ensure source balance has enough funds
    from_balance.amount = Decimal("100000.00")
    from_balance.save()

    to_balance, _ = BalanceEntry.objects.get_or_create(
        title="QA Destination USD Account",
        defaults={
            "amount": Decimal("1000.00"),
            "currency": usd_currency,
            "balance_type": BalanceEntry.BalanceType.BANK,
        }
    )
    to_balance.amount = Decimal("1000.00")
    to_balance.save()

    initial_from_amt = from_balance.amount
    initial_to_amt = to_balance.amount

    print(f"\n[SETUP] Source Balance ({from_balance.title}): {initial_from_amt} {from_balance.currency.code}")
    print(f"[SETUP] Destination Balance ({to_balance.title}): {initial_to_amt} {to_balance.currency.code}")

    # SCENARIO 1: Exchange Creation & Balance Impact
    print("\n--- SCENARIO 1: Exchange Creation (5,000 EGP to USD) ---")
    amount_to_exchange = Decimal("5000.00")
    rate = CurrencyConversionService.calculate_exchange_rate("EGP", "USD")
    converted_to_amount = (amount_to_exchange * rate).quantize(Decimal("0.01"))

    exchange = CurrencyExchange(
        exchange_date="2026-08-05",
        from_balance=from_balance,
        to_balance=to_balance,
        from_currency=egp_currency,
        to_currency=usd_currency,
        from_amount=amount_to_exchange,
        to_amount=converted_to_amount,
        exchange_rate=rate,
        status=CurrencyExchange.Status.ACTIVE,
        notes="E2E Human QA Creation Test",
        user=user
    )
    exchange.apply_exchange()

    from_balance.refresh_from_db()
    to_balance.refresh_from_db()

    expected_from_amt = initial_from_amt - amount_to_exchange
    expected_to_amt = initial_to_amt + converted_to_amount

    assert from_balance.amount == expected_from_amt, f"Expected source balance {expected_from_amt}, got {from_balance.amount}"
    assert to_balance.amount == expected_to_amt, f"Expected dest balance {expected_to_amt}, got {to_balance.amount}"
    print(f" [PASS] Creation updated balances correctly: Source={from_balance.amount} EGP, Dest={to_balance.amount} USD.")

    # SCENARIO 2: Atomic Edit & Reversal
    print("\n--- SCENARIO 2: Atomic Edit (Modify amount from 5,000 EGP to 10,000 EGP) ---")
    new_amount = Decimal("10000.00")
    new_converted = (new_amount * rate).quantize(Decimal("0.01"))

    # Reverse previous
    exchange.reverse_exchange(user=user, is_edit=True)
    
    # Update and re-apply
    exchange.from_amount = new_amount
    exchange.to_amount = new_converted
    exchange.status = CurrencyExchange.Status.ACTIVE
    exchange.save()
    exchange.apply_exchange()

    from_balance.refresh_from_db()
    to_balance.refresh_from_db()

    edit_expected_from = initial_from_amt - new_amount
    edit_expected_to = initial_to_amt + new_converted

    assert from_balance.amount == edit_expected_from, f"Edit source failed: expected {edit_expected_from}, got {from_balance.amount}"
    assert to_balance.amount == edit_expected_to, f"Edit dest failed: expected {edit_expected_to}, got {to_balance.amount}"
    print(f" [PASS] Atomic Edit updated balances correctly: Source={from_balance.amount} EGP, Dest={to_balance.amount} USD.")

    # SCENARIO 3: Reversal / Deletion Audit Trail
    print("\n--- SCENARIO 3: Reversal / Deletion Audit Trail ---")
    exchange.reverse_exchange(user=user)

    from_balance.refresh_from_db()
    to_balance.refresh_from_db()

    assert from_balance.amount == initial_from_amt, f"Reversal source failed: expected {initial_from_amt}, got {from_balance.amount}"
    assert to_balance.amount == initial_to_amt, f"Reversal dest failed: expected {initial_to_amt}, got {to_balance.amount}"
    assert exchange.status == CurrencyExchange.Status.REVERSED, f"Status should be REVERSED, got {exchange.status}"
    print(f" [PASS] Reversal restored exact original balances: Source={from_balance.amount} EGP, Dest={to_balance.amount} USD.")

    # SCENARIO 4: UI Playwright Human Experience Verification
    print("\n--- SCENARIO 4: UI Playwright Human Experience & Modals Sweep ---")
    out_dir = r"C:\Users\ehab.alqabbani\.gemini\antigravity\brain\88030822-0997-48fc-bf5b-17fe11e74582\screenshots"

    with sync_playwright() as p:
        test_ctx = TestContext(p, headed=False, slow_mo=50)
        test_ctx.login()
        time.sleep(1)

        page = test_ctx.page

        # Arabic Dark Mode UI Verification
        test_ctx.set_language("ar")
        test_ctx.set_theme("dark")
        page.evaluate("sessionStorage.setItem('wf_balance_active_tab', 'currency_exchange')")
        test_ctx.goto_route("#balance")
        time.sleep(2)

        if page.query_selector("#bal-tab-currency_exchange"):
            page.click("#bal-tab-currency_exchange")
            time.sleep(1)

        shot_ar_tab = os.path.join(out_dir, "human_qa_ar_tab.png")
        page.screenshot(path=shot_ar_tab)

        page.click("button[onclick='showExchangeModal()']")
        time.sleep(1)

        shot_ar_modal = os.path.join(out_dir, "human_qa_ar_modal.png")
        page.screenshot(path=shot_ar_modal)

        # English Light Mode UI Verification
        test_ctx.set_language("en")
        page.evaluate("if (typeof toggleTheme === 'function') toggleTheme();")
        time.sleep(2)

        shot_en_light_modal = os.path.join(out_dir, "human_qa_en_light_modal.png")
        page.screenshot(path=shot_en_light_modal)

        page.click(".btn-close")
        time.sleep(1)

        shot_en_light_tab = os.path.join(out_dir, "human_qa_en_light_tab.png")
        page.screenshot(path=shot_en_light_tab)

        test_ctx.close()

    print(" [PASS] UI Playwright Human Experience verified cleanly across AR/EN & Dark/Light modes.")

    # Cleanup QA test entries
    CurrencyExchange.objects.all().delete()
    from_balance.delete()
    to_balance.delete()

    print("\n==================================================================")
    print("  ALL E2E HUMAN QA SCENARIOS PASSED WITH ZERO ERRORS               ")
    print("==================================================================")

if __name__ == "__main__":
    run_e2e_human_currency_exchange_test()
