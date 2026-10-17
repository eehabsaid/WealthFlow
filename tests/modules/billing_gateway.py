"""Billing module phase: Paymob gateway settings (Gulf accounts) + return URL.

Read-only against the shared admin session: it never saves gateway settings.
 1. Settings > Billing Plans shows the main account fields plus a SAR and an AED regional block.
 2. The settings API refuses a non-paymob.com host (400) and a bad currency code (400).
 3. Stripe card: fields shown, bad currencies refused (400), webhook refuses unsigned posts (403) and GET (405).
 4. /billing/paymob/return/ lands the logged-in customer on #billing-plans without activating anything.

NOTE: tests/core/test_context.py registers ONE global dialog handler; do not add another page.on("dialog") here.
"""

POST_JS = """async (body) => {
    const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
    const r = await fetch('/api/settings/billing/gateway/', {
        method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
        body: JSON.stringify(body)});
    return r.status;
}"""


def _step(reporter, screenshot_logger, page, name, ok, detail, tab):
    shot = screenshot_logger.capture(page, "billing", tab, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "Billing", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def check_gateway_settings(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#settings-billing")   # the tab route (there is no global switchSettingsTab)
    page.wait_for_timeout(2000)
    reporter.tabs_visited.add("Billing -> Gateway settings")
    ids = ["paymobApiKey", "paymobDefaultCurrencies"] + [
        f"paymobRegion_{c}_{f}" for c in ("SAR", "AED") for f in ("base_url", "api_key", "hmac_secret", "integration_id", "iframe_id")
    ]
    missing = [i for i in ids if not page.query_selector(f"#{i}")]
    _step(reporter, screenshot_logger, page, "Gateway settings show main + SAR/AED regional accounts",
          not missing, f"missing_inputs={missing}", "gateway_settings")

    bad_host = page.evaluate(POST_JS, {"regions": {"SAR": {"base_url": "evil.example.com"}}})
    bad_code = page.evaluate(POST_JS, {"regions": {"sar!": {}}})
    _step(reporter, screenshot_logger, page, "Gateway settings reject non-Paymob host and bad currency code",
          bad_host == 400 and bad_code == 400, f"bad_host={bad_host} bad_code={bad_code}", "gateway_validation")

    context.goto_route("")
    landed = page.evaluate("fetch('/billing/paymob/return/', {redirect: 'manual'}).then(r => r.type)")
    page.goto(page.url.split('#')[0].rstrip('/') + "/billing/paymob/return/")
    page.wait_for_timeout(1500)
    ok = page.evaluate("window.location.hash") == "#billing-plans"
    _step(reporter, screenshot_logger, page, "Paymob return URL lands on the Plans page", ok,
          f"hash={page.evaluate('window.location.hash')} fetch_type={landed}", "paymob_return")


def check_stripe_settings(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#settings-billing")
    page.wait_for_timeout(2000)
    missing = [i for i in ("stripeSecretKey", "stripeWebhookSecret", "stripeCurrencies") if not page.query_selector(f"#{i}")]
    _step(reporter, screenshot_logger, page, "Stripe card shows secret key, webhook secret and currencies", not missing, f"missing_inputs={missing}", "stripe_settings")
    stripe_post = "async (b) => { const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || ''; return (await fetch('/api/settings/billing/stripe/', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf}, body: JSON.stringify(b)})).status; }"
    hook = "async (m) => (await fetch('/api/billing/stripe/webhook/', {method: m, body: m === 'POST' ? '{}' : undefined})).status"
    bad_cur, unsigned, wrong_verb = page.evaluate(stripe_post, {"stripe_currencies": "US"}), page.evaluate(hook, "POST"), page.evaluate(hook, "GET")
    _step(reporter, screenshot_logger, page, "Stripe validation and webhook guards", bad_cur == 400 and unsigned == 403 and wrong_verb == 405,
          f"bad_currency={bad_cur} unsigned_webhook={unsigned} get_webhook={wrong_verb}", "stripe_guards")
