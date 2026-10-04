"""WealthFlow QA Module - AI answer feedback and Learned Answers (Zip 2, part C).

No LLM is needed: the thumbs bar is rendered with the real UI function, the real endpoints are called from the
page, and the Learned Answers modal is opened exactly as the sidebar card does. (Chat answers themselves are
covered by the Django tests with a stub model.)
"""

_FETCH = """async ([url, method, body]) => {
  const res = await fetch(url, {method, headers: {"Content-Type": "application/json",
    "X-CSRFToken": (window.wfGetCsrfToken && window.wfGetCsrfToken()) || ""}, body: body ? JSON.stringify(body) : undefined});
  let data = null; try { data = await res.json(); } catch (e) {}
  return {status: res.status, data};
}"""


def _step(reporter, screenshot_logger, page, name, ok, detail, shot_name):
    shot = screenshot_logger.capture(page, "ai", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _run(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input, #ai-chat-input", timeout=8000)

    # 1. API contract (real endpoints, real session)
    empty = page.evaluate(_FETCH, ["/api/financial-advisor/ai/feedback/", "GET", None])
    ok = empty["status"] == 200 and empty["data"].get("items") == []
    _step(reporter, screenshot_logger, page, "Feedback list endpoint is empty for a new user", ok, f"GET feedback -> {empty}", "feedback_list")
    missing = page.evaluate(_FETCH, ["/api/financial-advisor/ai/messages/99999999/feedback/", "POST", {"rating": 1}])
    bad = page.evaluate(_FETCH, ["/api/financial-advisor/ai/messages/99999999/feedback/", "POST", {"rating": 5}])
    ok = missing["status"] == 404 and bad["status"] == 400
    _step(reporter, screenshot_logger, page, "Feedback rejects unknown message (404) and bad rating (400)", ok, f"{missing} / {bad}", "feedback_errors")

    # 2. Thumbs bar renders under an assistant answer and is absent under a user message
    page.evaluate("""() => {
      _appendMessage("user", "where do I record a laptop?", null, null, new Date().toISOString());
      _appendMessage("assistant", "Sample answer", [], [], new Date().toISOString(), 99999999, 0);
    }""")
    bars = page.query_selector_all(".ai-ws-feedback")
    ok = len(bars) == 1 and page.query_selector(".ai-ws-fb-up") is not None and page.query_selector(".ai-ws-fb-down") is not None
    _step(reporter, screenshot_logger, page, "Thumbs bar shows under the assistant answer only", ok, f"{len(bars)} feedback bar(s)", "thumbs_bar")

    # 3. Clicking a thumb on a message that does not exist shows the inline error (no silent failure)
    page.click(".ai-ws-fb-up")
    page.wait_for_selector(".ai-ws-fb-error:not([hidden])", timeout=5000)
    err = page.inner_text(".ai-ws-fb-error").strip()
    ok = bool(err) and page.query_selector(".ai-ws-fb-up.active") is None
    _step(reporter, screenshot_logger, page, "Failed feedback shows an error and keeps the thumb inactive", ok, f"error text: {err!r}", "thumbs_error")

    # 4. Learned Answers modal opens from the sidebar card and shows the empty state
    page.click("#ai-ws-card-learned-answers")
    page.wait_for_selector("#la-modal-body", timeout=5000)
    page.wait_for_selector("#la-empty", timeout=5000)
    ok = page.query_selector("#la-empty") is not None
    _step(reporter, screenshot_logger, page, "Learned Answers modal opens with empty state", ok, "empty state visible", "learned_answers")
    page.evaluate("() => { if (window.closeModal) closeModal(); }")
    reporter.pages_visited.add("WealthFlow AI -> Learned Answers")


def test_ai_learning(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:  # a failed check must be reported, not abort the rest of the suite
        shot = screenshot_logger.capture(context.page, "ai", "learning", "error", "fail", "fail")
        reporter.add_step("AI feedback / Learned Answers", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
