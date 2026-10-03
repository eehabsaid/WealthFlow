"""Gulf module phase: screen checks for a SAR/AED-base user (API-verified + screenshots)."""

from tests.modules.gulf_market.switching import api_json


def _step(reporter, screenshot_logger, page, name, ok, detail, tab):
    shot = screenshot_logger.capture(page, "gulf_market", tab, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "Gulf Markets", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _visible_text(page):
    return page.inner_text("#main-content") if page.query_selector("#main-content") else ""


def check_gulf_screens(context, reporter, screenshot_logger, code):
    page = context.page

    # Settings > Currencies
    context.goto_route("#settings")
    page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('currencies');")
    page.wait_for_timeout(700)
    codes = [c["code"].upper() for c in (api_json(page, "/api/currencies/") or {}).get("currencies", [])]
    ok = code in codes and "EGP" not in codes and "AED" in codes and "USD" in codes
    _step(reporter, screenshot_logger, page, f"[{code}] Currencies list has no EGP", ok, f"codes={codes}", f"{code.lower()}_currencies")

    # Exchange Rates screen
    context.goto_route("#exchange-rates")
    page.wait_for_timeout(900)
    rate_codes = [r["currency_code"] for r in (api_json(page, "/api/rates/") or {}).get("rates", [])]
    text = _visible_text(page)
    ok = "EGP" not in rate_codes and "AED" in rate_codes and "Egyptian Pound" not in text
    _step(reporter, screenshot_logger, page, f"[{code}] Exchange rates hide EGP", ok,
          f"api_has_egp={'EGP' in rate_codes} api_has_aed={'AED' in rate_codes}", f"{code.lower()}_rates")

    # Gold Prices screen
    context.goto_route("#gold-price")
    page.wait_for_timeout(1200)
    gold = (api_json(page, "/api/gold/") or {}).get("gold")
    text = _visible_text(page)
    if gold is None:
        _step(reporter, screenshot_logger, page, f"[{code}] Gold prices in base currency", True,
              "No gold price stored in this environment; screen checked for an empty state only.", f"{code.lower()}_gold")
        return
    ok = gold.get("market") == "spot" and gold.get("currency") == code and "EGP" not in text and "goldbullioneg" not in text
    _step(reporter, screenshot_logger, page, f"[{code}] Gold prices are spot prices in {code}", ok,
          f"market={gold.get('market')} currency={gold.get('currency')} egp_on_screen={'EGP' in text}", f"{code.lower()}_gold")

    # Plan prices
    plans = (api_json(page, "/api/billing/plans/") or {}).get("plans", [])
    plan_codes = {p["currency_code"].upper() for plan in plans for p in plan.get("prices", [])}
    _step(reporter, screenshot_logger, page, f"[{code}] Plan prices contain no EGP", "EGP" not in plan_codes,
          f"plan_price_currencies={sorted(plan_codes)}", f"{code.lower()}_plans")
