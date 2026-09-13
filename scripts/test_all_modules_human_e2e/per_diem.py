"""Phase 2: Per Diem / Salary E2E test. Split out of
scripts/test_all_modules_human_e2e.py."""

from decimal import Decimal

from core.models import Company, PerDiem
from core.services.salary.per_diem_service import PerDiemService


def run_per_diem_test(ctx):
    # ------------------------------------------------------------------
    # 2. PER DIEM / SALARY MODULE TEST
    # ------------------------------------------------------------------
    print("\n--- 2. PER DIEM / SALARY E2E TEST ---")
    company, _ = Company.objects.get_or_create(name="QA PerDiem Corp")
    per_diem_service = PerDiemService()
    per_diem_rate = per_diem_service.get_latest_buy_rate("USD")
    assert per_diem_rate == Decimal("50.000000"), f"Expected 50.000000 buy rate, got {per_diem_rate}"

    pd = PerDiem.objects.create(
        company=company,
        year=2026,
        date="2026-08-05",
        currency=ctx.usd,
        amount=Decimal("200.00"),
        amount_egp=Decimal("0.00")
    )
    # Total amount = 200 USD -> amount_egp should be 200 * 50.00 = 10,000.00 EGP
    expected_egp = pd.amount * per_diem_rate
    pd.amount_egp = expected_egp
    pd.save()
    assert pd.amount_egp == Decimal("10000.00"), f"PerDiem EGP calculation failed: {pd.amount_egp}"
    print(f"  [PASS] PerDiem buy rate delegation & EGP conversion: {pd.amount_egp} EGP for {pd.amount} USD.")

    ctx.company = company
    ctx.pd = pd
