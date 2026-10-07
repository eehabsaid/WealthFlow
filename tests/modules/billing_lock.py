"""Billing E2E phase: a lapsed trial/subscription locks the app to the upgrade page.

Runs inside the permission-less `testuser` session of tests/modules/billing.py. When that account's trial/subscription
has ended it must: bounce every other page back to #billing-plans, get HTTP 402 {"error": "subscription_required"}
from the data API, and still be able to use the billing endpoints. If the account is still in an active trial the
steps SKIP (nothing to lock) instead of failing.
"""

_GET = "async (u) => { const r = await fetch(u); let b = null; try { b = await r.json(); } catch (e) {} return {status: r.status, body: b}; }"


def check_lapsed_lock(page, reporter, screenshot_logger):
    status = page.evaluate(_GET, "/api/billing/status/")
    sub = (status.get("body") or {}).get("subscription") or {}
    if status["status"] != 200 or sub.get("has_access") is not False:
        reporter.add_step("Lapsed trial locks the app", "Billing", "SKIP",
                          f"Account is not lapsed (status={sub.get('status')!r}); nothing to lock.")
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
