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
    # Data-independent: the test account may already hold rated answers, so assert the contract and
    # relate every later check to this starting state (the "empty for a NEW user" case is covered by
    # core/tests/ai/test_ai_feedback_learning.py with a fresh user).
    listing = page.evaluate(_FETCH, ["/api/financial-advisor/ai/feedback/", "GET", None])
    items = (listing["data"] or {}).get("items")
    shape_ok = isinstance(items, list) and all(
        isinstance(it, dict) and {"message_id", "rating", "question"} <= set(it) and it["rating"] in (1, -1)
        for it in items
    )
    ok = listing["status"] == 200 and shape_ok
    count = len(items) if isinstance(items, list) else -1
    _step(reporter, screenshot_logger, page, "Feedback list endpoint returns this user's rated answers", ok,
          f"GET feedback -> status={listing['status']} items={count} shape_ok={shape_ok}", "feedback_list")
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
    # The modal shows the empty state iff the list is empty, otherwise exactly one row per rated answer.
    page.wait_for_selector("#la-empty, .la-row", timeout=5000)
    rows = len(page.query_selector_all(".la-row"))
    empty_shown = page.query_selector("#la-empty") is not None
    ok = (empty_shown and count == 0 and rows == 0) or (not empty_shown and count > 0 and rows == count)
    _step(reporter, screenshot_logger, page, "Learned Answers modal matches the rated-answer list (empty state or one row each)", ok,
          f"api_items={count} rows={rows} empty_state={empty_shown}", "learned_answers")
    page.evaluate("() => { if (window.closeModal) closeModal(); }")
    reporter.pages_visited.add("WealthFlow AI -> Learned Answers")


def test_ai_learning(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:  # a failed check must be reported, not abort the rest of the suite
        shot = screenshot_logger.capture(context.page, "ai", "learning", "error", "fail", "fail")
        reporter.add_step("AI feedback / Learned Answers", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
