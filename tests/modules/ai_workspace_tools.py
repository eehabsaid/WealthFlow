"""WealthFlow QA Module - AI workspace tools: chat search / rename, file attachments, insights, action cards, charts, voice sample.

No LLM is needed: the real endpoints are called from the page with the real session, and the real page functions draw the
cards and charts. What cannot run without a model (the model proposing an action) is covered by the Django tests.
"""

_FETCH = """async ([url, method, body]) => {
  const res = await fetch(url, {method, headers: {"Content-Type": "application/json",
    "X-CSRFToken": (window.wfGetCsrfToken && window.wfGetCsrfToken()) || ""}, body: body ? JSON.stringify(body) : undefined});
  let data = null; try { data = await res.json(); } catch (e) {}
  return {status: res.status, data};
}"""
_API = "/api/financial-advisor/ai/"
_SAMPLE_CARD = {"id": 987654, "kind": "action", "status": "pending", "payload": {"record": "expense", "op": "edit", "rows": [{"label": "description", "before": "lunch", "after": "dinner"}]}}
_SAMPLE_CHART = {"kind": "chart", "payload": {"type": "bar", "title": "Expenses by month", "labels": ["Jan", "Feb"], "series": [{"name": "Expenses", "values": [10, 20]}], "unit": "EGP"}}


def _step(reporter, screenshot_logger, page, name, ok, detail, shot_name):
    shot = screenshot_logger.capture(page, "ai", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _run(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input", timeout=8000)

    # 1. Chat management: create a chat, rename it in the sidebar, find it with the search box
    made = page.evaluate(_FETCH, [_API + "conversations/", "POST", {"title": "E2E tools chat"}])
    conv_id = ((made["data"] or {}).get("conversation") or {}).get("id")
    page.evaluate("() => _fetchAIChatConversations()")
    page.wait_for_selector(f'.ai-ws-conv-item[data-conv-id="{conv_id}"]', timeout=5000)
    page.evaluate(f"() => AICM.rename('{conv_id}')")
    page.fill(".ai-ws-rename-input", "E2E renamed chat")
    page.press(".ai-ws-rename-input", "Enter")
    page.wait_for_function("(id) => (document.querySelector(`.ai-ws-conv-item[data-conv-id=\"${id}\"] .ai-ws-conv-title`) || {}).textContent === 'E2E renamed chat'", arg=str(conv_id), timeout=5000)
    page.fill("#ai-ws-conv-search", "renamed chat")
    page.wait_for_selector(".ai-ws-conv-item .ai-ws-conv-title", timeout=5000)
    found = "E2E renamed chat" in page.inner_text("#ai-ws-conv-list")
    _step(reporter, screenshot_logger, page, "Chat can be renamed in the sidebar and found with the search box", found, f"conversation={conv_id}", "tools_chat_manage")
    page.fill("#ai-ws-conv-search", "")
    page.evaluate(_FETCH, [_API + f"conversations/{conv_id}/", "DELETE", None])

    # 2. Attach a file through the real file input; the chip shows and the server read it
    page.set_input_files("#ai-ws-attach-input", files=[{"name": "e2e.csv", "mimeType": "text/csv", "buffer": b"item,cost\na,10\nb,32\n"}])
    page.wait_for_selector("#ai-ws-attach-chips .ai-attach-chip", timeout=8000)
    chip = page.inner_text("#ai-ws-attach-chips")
    _step(reporter, screenshot_logger, page, "Attaching a CSV file shows its chip (the server read it)", "e2e.csv" in chip, f"chip={chip!r}", "tools_attach")
    page.click("#ai-ws-attach-chips .ai-attach-chip a")
    page.wait_for_function("() => !document.querySelector('#ai-ws-attach-chips .ai-attach-chip')", timeout=5000)
    bad = page.evaluate("""async () => { const f = new FormData(); f.append("file", new Blob(["x"]), "bad.exe");
      const r = await fetch("/api/financial-advisor/ai/attachments/", {method: "POST", headers: {"X-CSRFToken": window.wfGetCsrfToken()}, body: f}); return r.status; }""")
    _step(reporter, screenshot_logger, page, "An unsupported file type is refused", bad == 400, f"status={bad}", "tools_attach_bad")

    # 3. Insights endpoint and bell
    ins = page.evaluate(_FETCH, [_API + "insights/", "GET", None])
    ok = ins["status"] == 200 and isinstance((ins["data"] or {}).get("insights"), list)
    _step(reporter, screenshot_logger, page, "Insights endpoint returns this user's insights", ok, f"status={ins['status']} count={len((ins['data'] or {}).get('insights', []))}", "tools_insights")

    # 4. Action card and chart are drawn by the real page code
    html = page.evaluate("(c) => { AIBlocks.remember({id: 1, blocks: [c]}); return window._aiMessageExtras.map(f => f({role: 'assistant', messageId: 1})).join(''); }", _SAMPLE_CARD)
    card_ok = "ai-act-card" in html and "Confirm" in html and "dinner" in html
    gone = page.evaluate(_FETCH, [_API + "blocks/987654/cancel/", "POST", None])
    _step(reporter, screenshot_logger, page, "Action card shows before/after with Confirm; unknown cards are refused (404)", card_ok and gone["status"] == 404, f"status={gone['status']}", "tools_action_card")
    svg = page.evaluate("(c) => AIChart.draw(c)", _SAMPLE_CHART)
    _step(reporter, screenshot_logger, page, "Chart is drawn as an SVG with its title and unit", "<svg" in svg and "Expenses by month" in svg and "EGP" in svg, f"len={len(svg)}", "tools_chart")

    # 5. Voice sample endpoint (system administrator)
    vs = page.evaluate(_FETCH, ["/api/settings/ai/speech/voice-sample/", "GET", None])
    _step(reporter, screenshot_logger, page, "Voice sample endpoint answers for the system administrator", vs["status"] == 200 and "has_sample" in (vs["data"] or {}), f"status={vs['status']}", "tools_voice")
    reporter.pages_visited.add("WealthFlow AI -> Workspace tools")


def test_ai_workspace_tools(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:  # a failed check must be reported, not abort the rest of the suite
        shot = screenshot_logger.capture(context.page, "ai", "tools", "error", "fail", "fail")
        reporter.add_step("AI workspace tools", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
