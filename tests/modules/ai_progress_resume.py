"""WealthFlow QA Module - Agent progress and Stop button while a document is written (and after the page is opened again).

Real browser, no model needed (the server side - the document phase keeping the step list and Stop flag, Stop ending the guide - is
covered by the Django tests):
  1. A progress payload from the document phase (status line + steps + can_stop) renders the "Step n/m" line, the step list and Stop.
  2. The same payload applied to a freshly built bubble (what opening a running conversation again does) renders them too.
"""

from tests.modules.e2e_settings import AI_ENGINE_PINS, fresh_state, pinned

PAYLOAD = {"status": "running", "step": 4, "max_steps": 24, "label": "Writing the document: Financial Advisor", "elapsed_s": 43,
           "can_stop": True, "steps": [{"n": 1, "tool": "app_data_models", "label": "Looking at your data tables", "status": "ok", "target": ""},
                                       {"n": 2, "tool": "generate_file", "label": "Building your docx file", "status": "ok", "target": ""}]}


def _check(page):
    text = page.inner_text("#ai-ws-thinking-status-text")
    rows = page.locator("#ai-ws-agent-steps li.ai-ws-agent-step").count()
    return "Step 4/24" in text and "Financial Advisor" in text and rows == 2 and page.locator("#ai-ws-agent-stop").is_visible(), text, rows


def _run(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input", timeout=15000)
    page.evaluate("() => _setLoadingUI(true)")
    page.evaluate("(d) => window._aiShowProgress(d)", PAYLOAD)
    ok1, text1, rows1 = _check(page)
    page.evaluate("() => _setLoadingUI(false)")               # a new page load: no bubble, no list, no button
    gone = page.locator("#ai-ws-agent-stop").count() == 0
    page.evaluate("() => _setLoadingUI(true)")                # reopening a running conversation builds the bubble again ...
    page.evaluate("(d) => window._aiShowProgress(d)", PAYLOAD)  # ... and shows the stored progress at once
    ok2, text2, rows2 = _check(page)
    page.evaluate("() => _setLoadingUI(false)")
    shot = screenshot_logger.capture(page, "ai", "progress_resume", "none", "view", "ok" if ok1 and gone and ok2 else "fail")
    reporter.add_step("AI progress: steps and Stop shown, also after reopening a running chat", "WealthFlow AI",
                      "PASS" if ok1 and gone and ok2 else "FAIL", f"first={text1!r}/{rows1} rows, cleared={gone}, reopened={text2!r}/{rows2} rows",
                      screenshot_path=shot)


def test_ai_progress_resume(context, reporter, screenshot_logger):
    try:
        with pinned({**AI_ENGINE_PINS}), fresh_state(["ai_chat_mode"]):
            _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "progress_resume_error", "none", "fail", "fail")
        reporter.add_step("AI progress resume", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
