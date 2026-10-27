"""WealthFlow QA Module - AI Agent reads screen data (the app_screen_data tool).

Real browser, real APIs (no model needed: the Agent loop with a scripted model is covered by core/tests/ai/screen_data/):
  1. The Cash Flow endpoint the tool wraps answers for the logged-in user with a projected balance and its event list, and the
     same endpoint with another scope changes the scope it reports (so a question's "all currencies" is honoured).
  2. The live step list shows the new step with its translated label (not the raw tool name) and the endpoint it reads.
No core.* imports.
"""

CASH_URL = "/api/financial-advisor/cash-flow-custom-projection/"
_GET = """async (url) => {
  const res = await fetch(url, {headers: {"Accept": "application/json"}});
  let data = null; try { data = await res.json(); } catch (e) {}
  return {status: res.status, data};
}"""
STEP = {"status": "running", "can_stop": True, "steps": [
    {"n": 1, "tool": "app_screen_data", "label": "Reading the screen data (cash flow projection)", "status": "ok", "target": "cash flow projection"},
    {"n": 2, "tool": "app_screen_data", "label": "Reading the screen data (/api/financial-advisor/cash-flow-custom-projection/)", "status": "running",
     "target": "/api/financial-advisor/cash-flow-custom-projection/"}]}


def _step(reporter, screenshot_logger, page, name, ok, detail, shot_name):
    shot = screenshot_logger.capture(page, "ai", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _endpoint(page, context, reporter, screenshot_logger):
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input", timeout=15000)
    base = page.evaluate(_GET, [CASH_URL + "?days=30"])
    total = page.evaluate(_GET, [CASH_URL + "?days=30&currency_scope=total_liquid"])
    b, t = base["data"] or {}, total["data"] or {}
    ok = (base["status"] == 200 and isinstance(b.get("projected_balance"), (int, float)) and isinstance(b.get("included_events"), list)
          and b.get("currency_scope") == "base_only" and t.get("currency_scope") == "total_liquid")
    _step(reporter, screenshot_logger, page, "AI screen data: the Cash Flow endpoint the tool reads", ok,
          f"status={base['status']}, scope={b.get('currency_scope')!r}/{t.get('currency_scope')!r}, balance={b.get('projected_balance')!r}, "
          f"events={len(b.get('included_events') or [])}", "screen_data_endpoint")


def _steps(page, context, reporter, screenshot_logger):
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input", timeout=15000)
    page.evaluate("() => _setLoadingUI(true)")
    page.evaluate("(d) => window._aiRenderAgentSteps(d)", STEP)
    texts = [t.strip() for t in page.locator("#ai-ws-agent-steps li.ai-ws-agent-step").all_inner_texts()]
    ok = len(texts) == 2 and "app_screen_data" not in " ".join(texts) and texts[0].startswith("Reading the screen data") and "cash-flow-custom-projection" in texts[1]
    _step(reporter, screenshot_logger, page, "AI screen data: live step label", ok, f"step texts={texts!r}", "screen_data_steps")
    page.evaluate("() => _setLoadingUI(false)")


def test_ai_screen_data(context, reporter, screenshot_logger):
    page = context.page
    try:
        _endpoint(page, context, reporter, screenshot_logger)
        _steps(page, context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(page, "ai", "screen_data_error", "none", "fail", "fail")
        reporter.add_step("AI screen data", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
    finally:
        context.goto_route("#ai")
