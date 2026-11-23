"""Settings module phase 10: Property Valuation rate-map scrape (button + real save endpoint, no Aqarmap traffic)."""

import json

from tests.modules.settings.common import open_settings_tab

SCRAPE_URL = "/api/settings/scrape-property-rates/"
_FAKE_MAP = {
    "by_city": {"Garden City": 22171.0, "Zamalek": 99000.0},
    "by_governorate": {"Cairo": 35000},
    "default": 20000,
    "source": "aqarmap_live+baseline",
}


def test_property_valuation_scrape(context, reporter, screenshot_logger):
    page = context.page
    try:
        opened = open_settings_tab(context, "property-valuation")

        # 1. The real endpoint in baseline-only mode (no network): saves the map and answers ok.
        real = page.evaluate(
            """async (url) => {
                const r = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json"},
                                           body: JSON.stringify({baseline_only: true})});
                return {status: r.status, body: await r.json()};
            }""",
            SCRAPE_URL,
        )
        body = real.get("body") or {}
        saved_ok = real.get("status") == 200 and body.get("ok") is True and body.get("source") == "baseline_only" and body.get("districts", 0) > 0
        reporter.add_step("Rate map save endpoint (baseline only)", "Settings", "PASS" if saved_ok else "FAIL", f"status={real.get('status')} source={body.get('source')} districts={body.get('districts')}")

        # 2. The Scrape button with a faked Aqarmap result: textarea and badge show the live data.
        fake = {"ok": True, "source": "aqarmap_live+baseline", "districts": 2, "governorates": 1, "reason": "", "rate_map_json": json.dumps(_FAKE_MAP, indent=2)}
        page.route(f"**{SCRAPE_URL}", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(fake)))
        open_settings_tab(context, "property-valuation")
        page.click("#btnScrapeAqarmap", timeout=15000)
        page.wait_for_function("document.getElementById('propertyValuationRateMap').value.includes('22171')", timeout=15000)
        badge = page.inner_text("#scrapeStatusBadge")
        shot = screenshot_logger.capture(page, "settings", "property_valuation_scrape", "scrapePropertyRates", "click", "ok")
        live_shown = "Aqarmap live" in badge and "2 districts" in badge
        reporter.add_step("Scrape button shows live rates", "Settings", "PASS" if (opened and live_shown) else "FAIL", f"badge={badge!r}", screenshot_path=shot)
    except Exception as ex:
        reporter.add_step("Property valuation scrape test", "Settings", "FAIL", f"Exception: {ex}")
    finally:
        page.unroute(f"**{SCRAPE_URL}")
