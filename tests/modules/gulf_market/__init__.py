"""
WealthFlow QA Module — Gulf markets (A5): a SAR / AED base user has no EGP anywhere.
For each of SAR and AED the module creates a throwaway Member user (admin API), logs in with an isolated browser,
completes the REAL onboarding wizard call with that default currency, and checks (API-verified, with screenshots of
the real screens):
  - Settings > Currencies lists no EGP row (and a SAR user can still pick AED).
  - The Exchange Rates screen shows AED and no EGP row.
  - The Gold Prices screen is priced in the base currency (spot, no EGP / goldbullioneg text).
  - Plan prices contain no EGP.
  - Every Financial Advisor tab is free of EGP and Performance gold history is spot in the base currency.
The throwaway user is always deleted afterwards; no existing account is modified.

Split into one file per phase (200-line rule):
  - switching.py — throwaway-user + API helpers
  - screens.py   — the screen checks
  - advisor.py   — Financial Advisor tabs / Performance gold

NOTE: tests/core/test_context.py registers ONE global dialog handler; do not add another page.on("dialog") here.
"""

from tests.core.test_context import TestContext
from tests.modules.gulf_market.advisor import check_advisor_no_egp
from tests.modules.gulf_market.screens import check_gulf_screens
from tests.modules.gulf_market.switching import GULF_TEST_PASSWORD, api_post, create_member_user, delete_user


def _run_for_code(context, reporter, screenshot_logger, code):
    admin_page = context.page
    reporter.tabs_visited.add(f"Gulf Markets -> {code}")
    user_id, username = create_member_user(admin_page, code)
    if user_id is None:
        reporter.add_step(f"[{code}] Create throwaway user", "Gulf Markets", "FAIL", str(username))
        return
    user_ctx = None
    try:
        user_ctx = TestContext(context.playwright, headed=context.headed, slow_mo=context.slow_mo,
                               device="desktop", theme=context.theme)
        if not user_ctx.login(username=username, password=GULF_TEST_PASSWORD):
            reporter.add_step(f"[{code}] Throwaway user login", "Gulf Markets", "FAIL", f"login failed for {username}")
            return
        done = api_post(user_ctx.page, "/api/onboarding/complete/", {"default_currency": code})
        if done.get("status") != 200:
            shot = screenshot_logger.capture(user_ctx.page, "gulf_market", code.lower(), "none", "onboarding", "fail")
            reporter.add_step(f"[{code}] Onboarding with default currency", "Gulf Markets", "FAIL",
                              f"onboarding refused: {done}", screenshot_path=shot)
            return
        reporter.add_step(f"[{code}] Onboarding with default currency", "Gulf Markets", "PASS",
                          f"wizard call accepted for {username}")
        user_ctx.goto_route("")   # reload so the shell reads the new base currency and the wizard is gone
        check_gulf_screens(user_ctx, reporter, screenshot_logger, code)
        check_advisor_no_egp(user_ctx, reporter, screenshot_logger, code)
    finally:
        if user_ctx is not None:
            user_ctx.close()
        removed = delete_user(admin_page, user_id)
        reporter.add_step(f"[{code}] Throwaway user removed", "Gulf Markets",
                          "PASS" if removed.get("status") == 200 else "FAIL", f"delete status {removed.get('status')}")


def test_gulf_market_module(context, reporter, screenshot_logger):
    context.goto_route("")
    reporter.pages_visited.add("Gulf Markets")
    for code in ("SAR", "AED"):
        _run_for_code(context, reporter, screenshot_logger, code)
