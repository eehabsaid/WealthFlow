"""Billing E2E phase: the 'Your data' card (export my data / delete my account) on the plans page.

Never actually deletes the account: the delete form is opened/cancelled, and the API is only poked with a missing
confirmation (must be refused with 400 and leave the user in place). Export is a real download check.
"""

_FETCH = (
    "async ([u, m, b]) => { const h = {'Content-Type': 'application/json'};"
    " const c = document.cookie.match(/csrftoken=([^;]+)/); if (c) h['X-CSRFToken'] = c[1];"
    " const r = await fetch(u, {method: m, headers: h, body: b}); let j = null;"
    " try { j = await r.json(); } catch (e) {} return {status: r.status, body: j}; }"
)


def check_account_data_card(page, reporter, screenshot_logger):
    page.evaluate("() => { window.location.hash = 'billing-plans'; }")
    page.wait_for_timeout(1200)
    card = page.query_selector("#wf-account-data .wf-account-card")
    has_buttons = bool(page.query_selector("#wf-account-export-btn")) and bool(page.query_selector("#wf-account-delete-btn"))
    shot = screenshot_logger.capture(page, "billing", "account_data", "card", "ok" if card else "fail", "ok" if card else "fail")
    reporter.add_step("Plans page shows the 'Your data' card with Export and Delete", "Billing",
                      "PASS" if card and has_buttons else "FAIL", f"card={bool(card)} buttons={has_buttons}", screenshot_path=shot)
    if not card:
        return

    page.click("#wf-account-delete-btn")
    page.wait_for_timeout(300)
    opened = page.eval_on_selector("#wf-account-delete-form", "e => !e.hidden")
    page.click("#wf-account-delete-form .btn-secondary")
    page.wait_for_timeout(300)
    closed = page.eval_on_selector("#wf-account-delete-form", "e => e.hidden")
    reporter.add_step("Delete my account: confirm form opens and cancels", "Billing", "PASS" if opened and closed else "FAIL",
                      f"opened={opened} closed_after_cancel={closed}")

    with page.expect_download(timeout=15000) as dl:
        page.click("#wf-account-export-btn")
    name = dl.value.suggested_filename
    reporter.add_step("Export my data downloads a JSON file", "Billing", "PASS" if name.endswith(".json") else "FAIL", f"file={name}")

    refused = page.evaluate(_FETCH, ["/api/account/delete/", "POST", "{\"password\": \"x\"}"])
    still = page.evaluate(_FETCH, ["/api/auth/me/", "GET", None])
    reporter.add_step("Delete without typed confirmation is refused and keeps the account", "Billing",
                      "PASS" if refused["status"] == 400 and still["status"] == 200 else "FAIL",
                      f"delete={refused['status']} me={still['status']}")
