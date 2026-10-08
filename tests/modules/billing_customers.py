"""Billing module phase: trial option + Customers table (sysadmin). Shared admin session; leaves data unchanged.
 1. Settings > Billing shows the trial checkbox and the Customers table (the seeded testuser is listed).
 2. The trial option round-trips (off, back on) through the API.
 3. Invalid actions are refused: unknown action 400, extend_trial days=0 400, refund of a non-paid invoice 400/404.

NOTE: tests/core/test_context.py registers ONE global dialog handler; do not add another page.on("dialog") here.
"""

_JS = """async ([method, url, body]) => {
    const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
    const r = await fetch(url, {method, headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
        body: body === null ? undefined : JSON.stringify(body)});
    let j = null; try { j = await r.json(); } catch (e) {}
    return {status: r.status, body: j};
}"""


def _step(reporter, screenshot_logger, page, name, ok, detail, tab):
    shot = screenshot_logger.capture(page, "billing", tab, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "Billing", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def check_customers_and_trial_option(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#settings-billing")
    page.wait_for_timeout(2500)
    reporter.tabs_visited.add("Billing -> Customers")
    box, table = page.query_selector("#trialOnAdminCreated"), page.query_selector("#customersTable")
    listed = bool(table) and "testuser" in (table.inner_text() or "")
    _step(reporter, screenshot_logger, page, "Billing settings show the trial option and the Customers table",
          bool(box) and listed, f"trial_checkbox={bool(box)} customers_table={bool(table)} testuser_listed={listed}", "customers")

    url = "/api/settings/billing/trial-options/"
    off = page.evaluate(_JS, ["PUT", url, {"trial_on_admin_created_users": False}])
    mid = page.evaluate(_JS, ["GET", url, None])
    on = page.evaluate(_JS, ["PUT", url, {"trial_on_admin_created_users": True}])
    ok = off["status"] == 200 and mid["body"]["trial_on_admin_created_users"] is False and on["body"]["trial_on_admin_created_users"] is True
    _step(reporter, screenshot_logger, page, "Trial option round-trips and is restored to ON", ok,
          f"off={off['status']} read_back={mid['body']} on={on['status']}", "trial_option")

    customers = page.evaluate(_JS, ["GET", "/api/settings/billing/customers/?q=testuser", None])["body"]["customers"]
    uid = customers[0]["user_id"] if customers else 0
    bad_action = page.evaluate(_JS, ["POST", f"/api/settings/billing/customers/{uid}/action/", {"action": "nope"}])["status"]
    bad_days = page.evaluate(_JS, ["POST", f"/api/settings/billing/customers/{uid}/action/", {"action": "extend_trial", "days": 0}])["status"]
    bad_refund = page.evaluate(_JS, ["POST", "/api/settings/billing/invoices/999999999/action/", {"action": "refund"}])["status"]
    _step(reporter, screenshot_logger, page, "Customer/invoice actions refuse invalid input",
          bad_action == 400 and bad_days == 400 and bad_refund == 404,
          f"unknown_action={bad_action} days_0={bad_days} refund_missing_invoice={bad_refund}", "customers_validation")
