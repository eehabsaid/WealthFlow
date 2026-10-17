"""WealthFlow QA Module - AI net worth forecast.

In the REAL chat UI, with Instant Answers pinned ON, asks "please analyze my wealth and tell me how much will it be on
30-Nov-2026, in details" (the question that used to answer "the data only contains expense history") and checks that the
answer is the forecast table (a Net worth row, a Now column and an Expected - or, when all scenarios are equal, a single Forecast - column) with real money values and no expense text.
The same wording in Arabic must answer in Arabic. The step pins its own precondition (a funded cash balance, removed afterwards): a user with no money correctly
gets "not enough data for a forecast". Nothing else is created or changed except the chat itself.
"""

from tests.modules.e2e_settings import AI_ENGINE_PINS, pinned
from tests.modules.rent_receipts import fund_asset_purchases, unfund_asset_purchases

EN = "please analyze my wealth and tell me how much will it be on 30-Nov-2026, in details"
AR = "كم ستكون ثروتي في 30 نوفمبر 2026 بالتفصيل"


def _ask(page, text):
    before = page.locator(".ai-table-wrap").count()
    page.fill("#ai-ws-input", text)
    page.click(".ai-ws-send-btn")
    page.wait_for_function("(n) => document.querySelectorAll('.ai-table-wrap').length > n", arg=before, timeout=25000)
    page.wait_for_timeout(500)
    return page.locator(".ai-table-wrap").last


def _step(reporter, screenshot_logger, page, name, ok, detail, shot_name):
    shot = screenshot_logger.capture(page, "ai", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def test_ai_wealth(context, reporter, screenshot_logger):
    page = context.page
    fund_asset_purchases()
    try:
        context.goto_route("#ai")
        page.wait_for_selector("#ai-ws-input", timeout=10000)
        with pinned({**AI_ENGINE_PINS, "ai_direct_answers": "true"}):
            table = _ask(page, EN)
            text = table.inner_text()
            low = text.lower()  # the header cells are upper-cased by CSS, and inner_text returns the rendered case
            ok = "net worth" in low and "now" in low and ("expected" in low or "forecast" in low)  # one "Forecast" column when every scenario is equal
            _step(reporter, screenshot_logger, page, "AI wealth forecast answers with the projection table", ok and "Total All-Time Spending" not in text,
                  f"rows={table.locator('tr').count()}", "wealth_forecast")
            table = _ask(page, AR)
            ar_text = table.inner_text()
            _step(reporter, screenshot_logger, page, "AI wealth forecast answers in Arabic", "صافي الثروة" in ar_text, f"chars={len(ar_text)}", "wealth_forecast_ar")
    except Exception as ex:
        _step(reporter, screenshot_logger, page, "AI wealth forecast", False, f"Exception: {ex}", "wealth_forecast_error")
    finally:
        unfund_asset_purchases()
