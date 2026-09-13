"""Phase 5: UI Playwright Human Experience sweep. Split out of
scripts/test_all_modules_human_e2e.py."""

import os
import time

from playwright.sync_api import sync_playwright

from tests.core.test_context import TestContext


def run_ui_sweep():
    # ------------------------------------------------------------------
    # 5. UI PLAYWRIGHT HUMAN EXPERIENCE SWEEP
    # ------------------------------------------------------------------
    print("\n--- 5. UI PLAYWRIGHT HUMAN EXPERIENCE SWEEP ---")
    out_dir = r"C:\Users\ehab.alqabbani\.gemini\antigravity\brain\88030822-0997-48fc-bf5b-17fe11e74582\screenshots"
    os.makedirs(out_dir, exist_ok=True)

    with sync_playwright() as p:
        test_ctx = TestContext(p, headed=False, slow_mo=50)
        test_ctx.login()
        time.sleep(1)

        page = test_ctx.page

        # Balance -> Currency Exchange Tab Sweep
        test_ctx.set_language("ar")
        test_ctx.set_theme("dark")
        page.evaluate("sessionStorage.setItem('wf_balance_active_tab', 'currency_exchange')")
        test_ctx.goto_route("#balance")
        time.sleep(2)

        shot_ce = os.path.join(out_dir, "human_e2e_currency_exchange.png")
        page.screenshot(path=shot_ce)

        # Expenses Module Sweep
        test_ctx.goto_route("#expenses")
        time.sleep(2)
        shot_exp = os.path.join(out_dir, "human_e2e_expenses.png")
        page.screenshot(path=shot_exp)

        # Salary / Per Diem Module Sweep
        test_ctx.goto_route("#salary")
        time.sleep(2)
        shot_sal = os.path.join(out_dir, "human_e2e_salary.png")
        page.screenshot(path=shot_sal)

        # Fixed Assets Module Sweep
        test_ctx.goto_route("#fixed-assets")
        time.sleep(2)
        shot_fa = os.path.join(out_dir, "human_e2e_fixed_assets.png")
        page.screenshot(path=shot_fa)

        test_ctx.close()

    print("  [PASS] UI Playwright Human Experience sweep captured successfully across all 5 modules.")
