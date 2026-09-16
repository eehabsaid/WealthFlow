"""
WealthFlow QA Module — Billing: Trial Banner Upgrade Flow
Tests:
 1. A permission-less user (zero assigned PagePermission rows — the
    normal state for a brand-new trial account before an admin assigns
    page access) sees the trial/expired banner.
 2. Clicking "Upgrade" in that banner actually lands on the Plans page
    (#billing-plans), instead of being silently bounced back to Welcome.

This is a regression test for a bug where route_dispatch.js's
welcome-only redirect ran before checking whether the target route
(billing-plans) was one of the routes explicitly exempted from the
page-permission check in routeAllowed(). Fixed by also exempting
"billing-plans" in that earlier guard.

Runs its own isolated browser + login (testuser / Eehabdev1) rather
than the shared admin session the rest of the suite runs under, since
the scenario specifically requires zero assigned page permissions —
the shared session is a fully-privileged account and wouldn't exercise
this code path at all.
"""

from tests.core.test_context import TestContext

BILLING_TEST_USERNAME = "testuser"
BILLING_TEST_PASSWORD = "Eehabdev1"


def test_billing_module(context, reporter, screenshot_logger):
    reporter.pages_visited.add("Billing — Trial Banner Upgrade Flow")

    billing_ctx = None
    try:
        billing_ctx = TestContext(
            context.playwright,
            headed=context.headed,
            slow_mo=context.slow_mo,
            device="desktop",
            theme=context.theme,
        )
        login_ok = billing_ctx.login(username=BILLING_TEST_USERNAME, password=BILLING_TEST_PASSWORD)
        if not login_ok:
            shot = screenshot_logger.capture(context.page, "billing", "upgrade_flow", "login", "fail", "fail")
            reporter.add_step(
                "Trial Banner Upgrade Flow — testuser login",
                "Billing",
                "FAIL",
                f"Could not authenticate as {BILLING_TEST_USERNAME}/{BILLING_TEST_PASSWORD}.",
                screenshot_path=shot,
            )
            return

        page = billing_ctx.page
        page.wait_for_timeout(800)

        upgrade_btn = page.query_selector(
            "#trial-banner-mount button.wf-billing-banner-btn, "
            "#trial-banner-mount .wf-billing-banner-btn"
        )
        if not upgrade_btn:
            shot = screenshot_logger.capture(page, "billing", "upgrade_flow", "banner", "fail", "fail")
            reporter.add_step(
                "Trial Banner Upgrade Flow — banner visible",
                "Billing",
                "FAIL",
                "No trial/expired banner Upgrade button found for testuser. Confirm "
                "testuser has an active trial/subscription and zero assigned page "
                "permissions (both are required to exercise this scenario).",
                screenshot_path=shot,
            )
            return

        screenshot_logger.capture(page, "billing", "upgrade_flow", "banner", "before_click", "ok")
        upgrade_btn.click()
        page.wait_for_timeout(1200)

        landed_hash = page.evaluate("() => window.location.hash.replace('#', '')")
        shot_after = screenshot_logger.capture(page, "billing", "upgrade_flow", "after_click", "landed", "ok")

        if landed_hash == "billing-plans":
            reporter.add_step(
                "Trial Banner Upgrade Flow",
                "Billing",
                "PASS",
                "Clicking Upgrade in the trial banner (as a permission-less user) "
                "correctly landed on the Plans page (#billing-plans).",
                screenshot_path=shot_after,
            )
        else:
            reporter.add_step(
                "Trial Banner Upgrade Flow",
                "Billing",
                "FAIL",
                f"Expected to land on #billing-plans, landed on '#{landed_hash}' instead "
                "(regression of the welcome-only-redirect bug).",
                screenshot_path=shot_after,
            )

        # Sanity: the hash changing isn't enough on its own — confirm the
        # Plans page actually rendered content.
        plans_grid = page.query_selector(".wf-plans-grid")
        reporter.add_step(
            "Plans Page Renders After Upgrade Click",
            "Billing",
            "PASS" if plans_grid else "FAIL",
            "Plans grid present on #billing-plans."
            if plans_grid
            else "Plans grid missing after navigating to #billing-plans.",
        )

    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "billing", "upgrade_flow", "error", "fail", "fail")
        reporter.add_step(
            "Trial Banner Upgrade Flow", "Billing", "FAIL", f"Exception: {ex}", screenshot_path=shot_err
        )
    finally:
        if billing_ctx:
            try:
                billing_ctx.browser.close()
            except Exception:
                pass
