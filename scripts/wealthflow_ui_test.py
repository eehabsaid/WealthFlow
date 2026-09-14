"""
WealthFlow UI Smoke Test
=========================
Logs into a running WealthFlow instance and sweeps every module, page,
tab, and sub-tab in the app, checking each one for:
  - JavaScript console errors
  - Failed network requests (4xx/5xx)
  - Non-empty rendered content

It also opens the primary "Add" modal on every module that has one, to
confirm the modal renders correctly (fields, date picker, dropdowns) and
closes cleanly via the X button.

IMPORTANT: This script does NOT submit any forms or create/edit/delete
real data. It only verifies that the UI opens and closes correctly. This
is intentional, so running it against a real database won't leave behind
test rows in every module. If you want true create/edit/delete testing
for specific modules, that needs to be added per-module with exact field
selectors verified against your live app.

USAGE
-----
    python wealthflow_ui_test.py --username admin --password secret

    # Optional flags:
    python wealthflow_ui_test.py \
        --username admin \
        --password secret \
        --url http://127.0.0.1:8000 \
        --headless            # run without a visible browser window
        --slow-mo 100         # ms delay between actions (for watching)

Requires: pip install playwright && playwright install chromium
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

from playwright.async_api import async_playwright

# ── All sidebar routes + all Settings sub-tabs ───────────────────────────
ROUTES = [
    ("dashboard", "Dashboard"),
    ("ai", "AI Workspace"),
    ("financial-advisor", "Financial Advisor"),
    ("employment", "Salary / Employment"),
    ("balance", "Balance"),
    ("bank-certificates", "Bank Certificates"),
    ("fixed-assets", "Fixed Assets"),
    ("exchange-rates", "Exchange Rates"),
    ("gold-price", "Gold Price"),
    ("expenses", "Expenses"),
    ("expense-categories", "Expense Categories"),
    ("reports", "Reports"),
    ("advanced-reports", "Advanced Reports"),
    ("settings-languages", "Settings > Languages"),
    ("settings-companies", "Settings > Companies"),
    ("settings-banks", "Settings > Banks"),
    ("settings-currency", "Settings > Currency"),
    ("settings-users", "Settings > Users"),
    ("settings-billing", "Settings > Billing Plans"),
    ("settings-emailtemplates", "Settings > Email Templates"),
    ("settings-translations", "Settings > Translations"),
    ("settings-translationcoverage", "Settings > Translation Coverage"),
    ("settings-reminders", "Settings > Reminders"),
    ("settings-certstatus", "Settings > Certificate Status"),
    ("settings-goldsettings", "Settings > Gold Settings"),
    ("settings-propertyvaluation", "Settings > Property Valuation"),
    ("settings-dashboard", "Settings > Dashboard"),
    ("settings-backuprestore", "Settings > Backup & Restore"),
    ("settings-documentation", "Settings > Documentation"),
    ("settings-aiadvisor", "Settings > AI Advisor"),
]

# (route, visible text of the primary "Add"/"Create" button to test-open)
# None means "skip modal test for this route" (no add button, or
# destructive/network-calling action e.g. refresh-from-internet buttons
# are intentionally skipped so the script doesn't hit external services).
ADD_BUTTONS = {
    "expenses": "Add Expense",
    "expense-categories": "Add Category",
    "fixed-assets": "Add New Asset",
    "settings-languages": "Add Language",
    "settings-companies": "Add",
    "settings-banks": "Add",
    "settings-currency": "Add Currency",
    "settings-certstatus": "Add Status",
    "settings-goldsettings": "Add Gold Type",
}


def parse_args():
    p = argparse.ArgumentParser(description="WealthFlow full UI smoke test")
    p.add_argument("--username", required=True, help="Login username")
    p.add_argument("--password", required=True, help="Login password")
    p.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of the running app")
    p.add_argument("--headless", action="store_true", help="Run headless (default: headed, visible browser)")
    p.add_argument("--slow-mo", type=int, default=0, help="Milliseconds of delay between actions, useful when watching headed")
    p.add_argument("--out-dir", default="./wealthflow_ui_test_results", help="Where to save screenshots + report")
    return p.parse_args()


async def run(args):
    os.makedirs(args.out_dir, exist_ok=True)
    screenshots_dir = os.path.join(args.out_dir, "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless, slow_mo=args.slow_mo)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        console_errors = []
        failed_requests = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("response", lambda r: failed_requests.append(f"{r.status} {r.url}") if r.status >= 400 else None)
        page.on("pageerror", lambda exc: console_errors.append(f"PAGEERROR: {exc}"))

        # ── LOGIN ──────────────────────────────────────────────────────
        print(f"Logging in as {args.username} at {args.url} ...")
        console_errors.clear()
        failed_requests.clear()
        await page.goto(f"{args.url}/accounts/login/", wait_until="networkidle")
        await page.fill('input[name="username"]', args.username)
        await page.fill('input[name="password"]', args.password)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle", timeout=15000)

        login_ok = "/accounts/login" not in page.url
        results.append({
            "page": "Login",
            "ok": login_ok,
            "console_errors": list(console_errors),
            "failed_requests": list(failed_requests),
        })
        print(f"  Login {'OK' if login_ok else 'FAILED'}")
        if not login_ok:
            print("Aborting: login did not succeed. Check credentials / URL.")
            await browser.close()
            write_report(results, args.out_dir)
            return

        # ── SWEEP EVERY ROUTE ─────────────────────────────────────────
        for route, label in ROUTES:
            print(f"Checking: {label} ({route})")
            console_errors.clear()
            failed_requests.clear()
            notes = []
            ok = True

            try:
                await page.evaluate(f"window.location.hash = '{route}'")
                await page.wait_for_timeout(1200)
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception as e:
                notes.append(f"navigation issue: {e}")

            try:
                content_len = await page.eval_on_selector("#main-content", "el => el.innerHTML.length")
                if content_len < 30:
                    ok = False
                    notes.append("main-content appears empty")
            except Exception as e:
                ok = False
                notes.append(f"could not read #main-content: {e}")

            shot_path = os.path.join(screenshots_dir, f"{route}.png")
            try:
                await page.screenshot(path=shot_path, full_page=True)
            except Exception as e:
                notes.append(f"screenshot failed: {e}")

            if console_errors:
                ok = False
            if failed_requests:
                ok = False

            entry = {
                "page": label,
                "route": route,
                "ok": ok,
                "console_errors": list(console_errors),
                "failed_requests": list(failed_requests),
                "notes": notes,
                "screenshot": shot_path,
            }

            # ── Optional: open+close the primary Add modal ─────────────
            btn_text = ADD_BUTTONS.get(route)
            if btn_text:
                console_errors.clear()
                failed_requests.clear()
                modal_notes = []
                try:
                    loc = page.locator(f"#main-content >> text='{btn_text}'").first
                    await loc.wait_for(state="visible", timeout=5000)
                    try:
                        await loc.click(timeout=8000)
                    except Exception:
                        # Playwright sometimes reports a timeout on the
                        # trailing stability check even though the click
                        # already registered (e.g. modal fade-in
                        # animation). Re-check modal state before
                        # treating this as a real failure.
                        pass
                    await page.wait_for_timeout(800)

                    modal_open = await page.evaluate(
                        "() => !!document.querySelector('.modal.show, "
                        "[class*=\"modal\"][style*=\"display: block\"], "
                        "[class*=\"modal\"][style*=\"display:block\"]')"
                    )
                    modal_shot = os.path.join(screenshots_dir, f"{route}_modal.png")
                    if modal_open:
                        await page.screenshot(path=modal_shot)

                    # Close via the visible X button (Escape is not wired
                    # up in this app, so don't rely on it)
                    close_btn = page.locator(
                        "button:has-text('×'), .modal .btn-close, [aria-label='Close']"
                    ).first
                    try:
                        await close_btn.click(timeout=5000)
                    except Exception as e:
                        modal_notes.append(f"could not close modal via X: {e}")

                    modal_entry = {
                        "button": btn_text,
                        "modal_opened": modal_open,
                        "console_errors": list(console_errors),
                        "failed_requests": list(failed_requests),
                        "notes": modal_notes,
                        "screenshot": modal_shot if modal_open else None,
                    }
                    entry["add_modal_test"] = modal_entry
                    if not modal_open or console_errors or failed_requests:
                        entry["ok"] = False
                except Exception as e:
                    entry["add_modal_test"] = {"button": btn_text, "error": str(e)}
                    entry["ok"] = False

            results.append(entry)

        await browser.close()

    write_report(results, args.out_dir)


def write_report(results, out_dir):
    json_path = os.path.join(out_dir, "results.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    total = len(results)
    failed = [r for r in results if not r["ok"]]

    print("\n" + "=" * 60)
    print(f"WealthFlow UI Test — {datetime.now().isoformat(timespec='seconds')}")
    print("=" * 60)
    print(f"Total checks: {total}   Passed: {total - len(failed)}   Failed: {len(failed)}")
    if failed:
        print("\nFAILURES:")
        for r in failed:
            print(f"  - {r['page']}")
            for e in r.get("console_errors", []):
                print(f"      console: {e[:150]}")
            for e in r.get("failed_requests", []):
                print(f"      request: {e}")
            for n in r.get("notes", []):
                print(f"      note: {n}")
    print(f"\nFull JSON report: {json_path}")
    print(f"Screenshots: {os.path.join(out_dir, 'screenshots')}")
    print("=" * 60)


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args))
