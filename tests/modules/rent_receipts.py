"""Fixed Assets phase: 'Rent received' settles the month's virtual rental income (rent counts once).

Fixture rental is created in the DISPOSABLE db and removed afterwards. Steps:
 1. Rental tab shows the 'Rent received' control for the current month.
 2. Clicking it records the deposit through the UI; the balance total does not grow by a second month of rent.
 3. Undo removes the receipt; the total returns to the virtual-rent value.
"""

from tests.modules.e2e_settings import django_exec, rows

NAME = "E2E Rent Flat"
FIXTURE = (
    "import datetime; from django.contrib.auth import get_user_model; from core.models import AssetRental, FixedAsset\n"
    "u = get_user_model().objects.get(username='eehab_said')\n"
    f"a = FixedAsset.objects.create(owner=u, name='{NAME}', asset_type='Real Estate', status='Owned', purchase_date=datetime.date(2026, 1, 1), purchase_price=1, current_market_value=1)\n"
    "AssetRental.objects.create(asset=a, monthly_rent=1000, occupancy_rate=50)\n"
)
CLEANUP = f"from core.models import FixedAsset; FixedAsset.objects.filter(name='{NAME}').delete()"
# A freshly seeded user owns no money, so buying an asset fails with matching_balance_entry_not_found. The asset steps
# pin their own precondition: one funded cash balance in the user's default currency, plus one asset so the portfolio
# PDF/Excel reports have something to report (they answer 404 "No fixed assets found" on an empty portfolio). Both are
# removed again afterwards.
FUND = (
    "from django.contrib.auth import get_user_model; from core.models import BalanceEntry, Currency; from core.services.shared.base_currency import get_user_base_code\n"
    "u = get_user_model().objects.get(username='eehab_said'); cur = Currency.objects.filter(owner=u, code__iexact=get_user_base_code(u)).first()\n"
    "BalanceEntry.objects.get_or_create(owner=u, title='E2E funding', defaults=dict(balance_type='cash', currency=cur, amount=100000000))\n"
    "import datetime; from core.models import FixedAsset\n"
    "FixedAsset.objects.get_or_create(owner=u, name='E2E Report Asset', defaults=dict(asset_type='Other', status='Owned', purchase_date=datetime.date(2026, 1, 1), purchase_price=1000, current_market_value=1000))\n"
)
UNFUND = "from core.models import BalanceEntry, FixedAsset; BalanceEntry.objects.filter(title='E2E funding').delete(); FixedAsset.objects.filter(name='E2E Report Asset').delete()"
TOTAL_JS = "fetch('/api/balance/').then(r => r.json()).then(d => d.summary.grand_total)"


def _step(reporter, screenshot_logger, page, name, ok, detail, tab):
    shot = screenshot_logger.capture(page, "fixed_assets", tab, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "Fixed Assets", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def check_rent_received(context, reporter, screenshot_logger):
    page = context.page
    django_exec(FIXTURE)
    try:
        asset_id = rows("SELECT id FROM core_fixedasset WHERE name = ?", (NAME,))[0][0]
        context.goto_route("#fixed-assets")
        page.wait_for_timeout(1500)
        before = page.evaluate(TOTAL_JS)
        page.evaluate(f"showFixedAssetDetails({asset_id})")
        page.wait_for_selector("#asset-rental-tab", timeout=10000)
        page.click("#asset-rental-tab")
        page.wait_for_selector("#rentReceivedBtn", timeout=8000)
        reporter.tabs_visited.add("Fixed Assets -> Rental -> Rent received")
        _step(reporter, screenshot_logger, page, "Rental tab offers 'Rent received' for the current month", True, "button visible", "rent_received_button")

        page.click("#rentReceivedBtn")
        page.wait_for_selector("#rentUndoBtn", timeout=8000)
        after = page.evaluate(TOTAL_JS)
        db = rows("SELECT amount FROM core_rentreceipt r JOIN core_assetrental a ON a.id = r.rental_id WHERE a.asset_id = ?", (asset_id,))
        _step(reporter, screenshot_logger, page, "Rent received is booked once (no second month of rent in the balance)",
              len(db) == 1 and abs(after - before) < 0.01, f"before={before} after={after} receipts={db}", "rent_received_recorded")

        page.click("#rentUndoBtn")
        page.wait_for_selector("#rentReceivedBtn", timeout=8000)
        back = page.evaluate(TOTAL_JS)
        _step(reporter, screenshot_logger, page, "Undo removes the receipt and restores the expected rent", abs(back - before) < 0.01,
              f"before={before} after_undo={back}", "rent_received_undo")
    except Exception as exc:  # a failing step must be reported, never swallowed
        reporter.add_step("Rent received flow", "Fixed Assets", "FAIL", f"Exception: {exc}")
    finally:
        django_exec(CLEANUP)


def fund_asset_purchases():
    django_exec(FUND)


def unfund_asset_purchases():
    django_exec(UNFUND)
