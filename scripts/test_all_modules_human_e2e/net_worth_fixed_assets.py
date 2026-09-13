"""Phase 4: Net Worth & Fixed Assets E2E test. Split out of
scripts/test_all_modules_human_e2e.py."""

from decimal import Decimal

from core.services.balance.net_worth_service import NetWorthService


def run_net_worth_fixed_assets_test(ctx):
    # ------------------------------------------------------------------
    # 4. NET WORTH & FIXED ASSETS MODULE TEST
    # ------------------------------------------------------------------
    print("\n--- 4. NET WORTH & FIXED ASSETS E2E TEST ---")
    nw_service = NetWorthService()
    rates = nw_service._latest_rates()
    assert rates.get("USD") == 50.0, f"NetWorth rates failed: USD={rates.get('USD')}"
    print(f"  [PASS] NetWorth Service loaded centralized rates: USD = {rates.get('USD')}")

    # Fixed Asset Creation via View API simulation
    from core.views.fixed_assets.fixed_asset_core_views import _resolve_asset_usd_rate_and_price
    fa_data = {
        "name": "QA Villa Asset",
        "asset_type": "Real Estate",
        "purchase_price": 5000000.00,
        "purchase_currency_id": ctx.egp.id
    }
    usd_rate, price_usd = _resolve_asset_usd_rate_and_price(fa_data)
    # USD rate for EGP against USD = 0.020000 (1/50). Purchase price USD = 5,000,000 / 50 = 100,000.00 USD
    assert usd_rate == Decimal("0.020000"), f"FA USD rate failed: {usd_rate}"
    assert price_usd == Decimal("100000.00"), f"FA USD price failed: {price_usd}"
    print(f"  [PASS] Fixed Asset USD Fallback Resolution: EGP {fa_data['purchase_price']} -> USD {price_usd} (rate={usd_rate}).")
