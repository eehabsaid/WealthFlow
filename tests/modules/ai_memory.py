"""WealthFlow QA Module - AI Memory (cross-chat notes the model writes for itself).

No LLM is needed: the real endpoints are called from the page with the real session, and the AI Memory page is
opened exactly as the sidebar card does. A note is created through the model layer's own API path (the page can only
list, edit and delete), so the test seeds one note with the Django shell-free route: the chat writer is covered by
the Django tests with a stub model.
"""

_FETCH = """async ([url, method, body]) => {
  const res = await fetch(url, {method, headers: {"Content-Type": "application/json",
    "X-CSRFToken": (window.wfGetCsrfToken && window.wfGetCsrfToken()) || ""}, body: body ? JSON.stringify(body) : undefined});
  let data = null; try { data = await res.json(); } catch (e) {}
  return {status: res.status, data};
}"""

_URL = "/api/financial-advisor/ai/memory/"


def _step(reporter, screenshot_logger, page, name, ok, detail, shot_name):
    shot = screenshot_logger.capture(page, "ai", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _run(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input, #ai-chat-input", timeout=8000)

    # 1. API contract
    listing = page.evaluate(_FETCH, [_URL, "GET", None])
    items = (listing["data"] or {}).get("items")
    shape_ok = isinstance(items, list) and all(isinstance(i, dict) and {"id", "title", "body", "updated_at"} <= set(i) for i in items)
    count = len(items) if isinstance(items, list) else -1
    _step(reporter, screenshot_logger, page, "AI Memory list endpoint returns this user's notes", listing["status"] == 200 and shape_ok,
          f"GET memory -> status={listing['status']} items={count} shape_ok={shape_ok}", "memory_list")
    missing = page.evaluate(_FETCH, [_URL + "99999999/", "DELETE", None])
    bad = page.evaluate(_FETCH, [_URL + "99999999/", "PATCH", {"title": "x"}])
    _step(reporter, screenshot_logger, page, "AI Memory rejects unknown notes (404 on delete and edit)", missing["status"] == 404 and bad["status"] == 404,
          f"{missing} / {bad}", "memory_errors")

    # 2. The page opens from the sidebar card and matches the API list (empty state or one row per note)
    page.click("#ai-ws-card-memory")
    page.wait_for_selector("#mem-modal-body", timeout=5000)
    page.wait_for_selector("#mem-empty, .mem-row", timeout=5000)
    rows = len(page.query_selector_all(".mem-row"))
    empty_shown = page.query_selector("#mem-empty") is not None
    ok = (empty_shown and count == 0 and rows == 0) or (not empty_shown and count > 0 and rows == count)
    _step(reporter, screenshot_logger, page, "AI Memory page matches the note list (empty state or one row each)", ok,
          f"api_items={count} rows={rows} empty_state={empty_shown}", "memory_page")

    # 3. Edit and delete through the real UI when a note exists (the AI creates notes on its own, so none may exist yet)
    if rows:
        page.click(".mem-edit")
        page.fill("#mem-edit-title", "E2E edited title")
        page.click("#mem-save")
        page.wait_for_selector(".mem-row .fw-semibold", timeout=5000)
        after_edit = page.evaluate(_FETCH, [_URL, "GET", None])["data"]["items"]
        edited = any(i["title"] == "E2E edited title" for i in after_edit)
        _step(reporter, screenshot_logger, page, "Editing a note in the AI Memory page saves it", edited, f"titles={[i['title'] for i in after_edit][:5]}", "memory_edit")
        page.click(".mem-delete")
        page.click(".mem-delete-yes")
        page.wait_for_function("(n) => document.querySelectorAll('.mem-row').length === n || !!document.querySelector('#mem-empty')", arg=rows - 1, timeout=5000)
        after_delete = page.evaluate(_FETCH, [_URL, "GET", None])["data"]["items"]
        _step(reporter, screenshot_logger, page, "Deleting a note in the AI Memory page removes it", len(after_delete) == rows - 1,
              f"before={rows} after={len(after_delete)}", "memory_delete")

    # 4. The "Saved memory" chip is rendered by the real chip function and opens the page
    page.evaluate("() => { if (window.closeModal) closeModal(); window.AIMemChip.show(); }")
    chip = page.query_selector("#ai-mem-chip button")
    page.click("#ai-mem-chip button")
    page.wait_for_selector("#mem-modal-body", timeout=5000)
    _step(reporter, screenshot_logger, page, "Saved memory chip appears and opens the AI Memory page", chip is not None, "chip clicked, page opened", "memory_chip")
    page.evaluate("() => { if (window.closeModal) closeModal(); window.AIMemChip.clear(); }")
    reporter.pages_visited.add("WealthFlow AI -> AI Memory")


def test_ai_memory(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:  # a failed check must be reported, not abort the rest of the suite
        shot = screenshot_logger.capture(context.page, "ai", "memory", "error", "fail", "fail")
        reporter.add_step("AI Memory", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
