"""WealthFlow QA Module — Owner setup helpers: AI default-key warning and Paymob regional 'Test connection'.

 1. Settings > AI Advisor shows the default-key warning exactly when the API says the default key is in use.
 2. Settings > Billing shows a Test connection button for SAR and AED.
 3. Clicking it never hangs and shows a clear message (nothing is charged; with no saved account it says nothing to test).
NOTE: tests/core/test_context.py registers ONE global dialog handler; do not add another page.on("dialog") here.
"""


def _step(reporter, shots, page, name, ok, detail, tab):
    shot = shots.capture(page, "owner_setup", tab, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "Settings", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _check_ai_warning(context, reporter, shots):
    page = context.page
    context.goto_route("#settings-aiadvisor")
    page.wait_for_timeout(2500)
    flag = page.evaluate("fetch('/api/settings/ai/').then(r => r.json()).then(d => d.encryption_key_default)")
    shown = page.locator("#aiDefaultKeyWarning").count() == 1
    _step(reporter, shots, page, "AI Advisor default-key warning matches the server state", shown == bool(flag),
          f"api_default_key={flag} warning_shown={shown}", "ai_key_warning")


def _check_paymob_test(context, reporter, shots):
    page = context.page
    context.goto_route("#settings-billing")
    page.wait_for_timeout(2500)
    buttons = {code: page.locator(f"[data-paymob-test='{code}']").count() for code in ("SAR", "AED")}
    _step(reporter, shots, page, "Billing settings show Test connection for SAR and AED", all(v == 1 for v in buttons.values()),
          f"buttons={buttons}", "paymob_buttons")
    if buttons["SAR"] != 1:
        return
    page.click("[data-paymob-test='SAR']")
    page.wait_for_timeout(4000)
    text = page.inner_text("#paymobTestResult_SAR").strip()
    _step(reporter, shots, page, "Test connection shows a clear result message", bool(text) and text != "…", f"message={text[:120]}", "paymob_result")


def test_owner_setup_module(context, reporter, shots):
    reporter.pages_visited.add("Settings — owner setup helpers")
    try:
        _check_ai_warning(context, reporter, shots)
        _check_paymob_test(context, reporter, shots)
    except Exception as ex:
        shot = shots.capture(context.page, "owner_setup", "error", "none", "fail", "fail")
        reporter.add_step("Owner setup module", "Settings", "FAIL", f"Exception: {ex}", screenshot_path=shot)
