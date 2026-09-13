"""Phase 1: Currency Exchange E2E test. Split out of
scripts/test_all_modules_human_e2e.py."""

from decimal import Decimal

from core.models import BalanceEntry, CurrencyExchange
from core.services.shared.currency_conversion_service import CurrencyConversionService


def run_currency_exchange_test(ctx):
    # ------------------------------------------------------------------
    # 1. CURRENCY EXCHANGE MODULE TEST
    # ------------------------------------------------------------------
    print("\n--- 1. CURRENCY EXCHANGE E2E TEST ---")
    bal_egp, _ = BalanceEntry.objects.get_or_create(
        title="QA CE Source EGP Account",
        defaults={"amount": Decimal("100000.00"), "currency": ctx.egp, "balance_type": BalanceEntry.BalanceType.CASH}
    )
    bal_egp.amount = Decimal("100000.00")
    bal_egp.save()

    bal_usd, _ = BalanceEntry.objects.get_or_create(
        title="QA CE Dest USD Account",
        defaults={"amount": Decimal("1000.00"), "currency": ctx.usd, "balance_type": BalanceEntry.BalanceType.BANK}
    )
    bal_usd.amount = Decimal("1000.00")
    bal_usd.save()

    # Create Exchange (5,000 EGP to USD)
    calc_rate, to_amt = CurrencyConversionService.convert_amount(Decimal("5000.00"), "EGP", "USD")
    ce = CurrencyExchange(
        exchange_date="2026-08-05",
        from_balance=bal_egp,
        to_balance=bal_usd,
        from_currency=ctx.egp,
        to_currency=ctx.usd,
        from_amount=Decimal("5000.00"),
        to_amount=to_amt,
        exchange_rate=calc_rate,
        status=CurrencyExchange.Status.ACTIVE,
        user=ctx.user
    )
    ce.apply_exchange()

    bal_egp.refresh_from_db()
    bal_usd.refresh_from_db()
    assert bal_egp.amount == Decimal("95000.00"), f"Source balance failed: {bal_egp.amount}"
    assert bal_usd.amount == Decimal("1000.00") + to_amt, f"Dest balance failed: {bal_usd.amount}"
    print(f"  [PASS] Currency Exchange Creation: EGP balance {bal_egp.amount}, USD balance {bal_usd.amount}")

    ce.reverse_exchange(user=ctx.user)
    bal_egp.refresh_from_db()
    bal_usd.refresh_from_db()
    assert bal_egp.amount == Decimal("100000.00"), "Reversal EGP failed"
    assert bal_usd.amount == Decimal("1000.00"), "Reversal USD failed"
    print("  [PASS] Currency Exchange Reversal restored exact balances.")

    ctx.bal_egp = bal_egp
    ctx.bal_usd = bal_usd
    ctx.ce = ce
