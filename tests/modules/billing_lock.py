"""Billing E2E phase: a lapsed trial/subscription locks the app to the upgrade page.

Runs in its own browser session as the seeded `lapsed_user` (scripts/e2e_seed.py: trial ended yesterday, so the
scenario is deterministic and never SKIPs). It must: bounce every other page back to #billing-plans, get HTTP 402
{"error": "subscription_required"} from the data API, and still be able to use the billing endpoints. If the seeded
account is not lapsed the step FAILS (the seed is broken), it no longer skips.
"""

from tests.core.test_context import TestContext

LAPSED_USERNAME = "lapsed_user"
LAPSED_PASSWORD = "Eehabdev1"

_GET = "async (u) => { const r = await fetch(u); let b = null; try { b = await r.json(); } catch (e) {} return {status: r.status, body: b}; }"


def check_lapsed_lock(context, reporter, screenshot_logger):
    lapsed_ctx = None
    try:
        lapsed_ctx = TestContext(context.playwright, headed=context.headed, slow_mo=context.slow_mo,
                                 device="desktop", theme=context.theme)
        if not lapsed_ctx.login(username=LAPSED_USERNAME, password=LAPSED_PASSWORD):
            reporter.add_step("Lapsed trial locks the app", "Billing", "FAIL",
                              f"Could not log in as seeded {LAPSED_USERNAME} (run scripts/e2e_seed.py).")
            return
        lapsed_ctx.page.wait_for_timeout(800)
        _run_lapsed_steps(lapsed_ctx.page, reporter, screenshot_logger)
    except Exception as ex:
        reporter.add_step("Lapsed trial locks the app", "Billing", "FAIL", f"Exception: {ex}")
    finally:
        if lapsed_ctx:
            try:
                lapsed_ctx.browser.close()
            except Exception:
                pass


def _run_lapsed_steps(page, reporter, screenshot_logger):
    status = page.evaluate(_GET, "/api/billing/status/")
    sub = (status.get("body") or {}).get("subscription") or {}
    if status["status"] != 200 or sub.get("has_access") is not False:
        reporter.add_step("Lapsed trial locks the app", "Billing", "FAIL",
                          f"Seeded {LAPSED_USERNAME} is not lapsed (status={sub.get('status')!r}); seed is broken.")
        return

    bounced = []
    for route in ("dashboard", "balance", "banks", "fixed-assets"):
        page.evaluate("(r) => { window.location.hash = r; }", route)
        page.wait_for_timeout(900)
        bounced.append((route, page.evaluate("() => window.location.hash.replace('#', '')")))
    ok = all(landed == "billing-plans" for _, landed in bounced)
    shot = screenshot_logger.capture(page, "billing", "lapsed_lock", "bounced", "ok" if ok else "fail", "ok" if ok else "fail")
    reporter.add_step("Lapsed trial: every other page bounces to the upgrade page", "Billing", "PASS" if ok else "FAIL",
                      f"route -> landed: {bounced}", screenshot_path=shot)

    blocked = {p: page.evaluate(_GET, p) for p in ("/api/balance/", "/api/banks/", "/api/expenses/", "/api/fixed-assets/")}
    all402 = all(r["status"] == 402 and (r["body"] or {}).get("error") == "subscription_required" for r in blocked.values())
    reporter.add_step("Lapsed trial: data API returns 402 subscription_required", "Billing", "PASS" if all402 else "FAIL",
                      str({p: r["status"] for p, r in blocked.items()}))

    plans = page.evaluate(_GET, "/api/billing/plans/")
    banner = page.query_selector("#trial-banner-mount .wf-billing-banner-expired")
    reporter.add_step("Lapsed trial: billing endpoints and expired banner still available", "Billing",
                      "PASS" if plans["status"] == 200 and banner else "FAIL",
                      f"plans={plans['status']} banner={'shown' if banner else 'missing'}")
