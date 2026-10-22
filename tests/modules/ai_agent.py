"""WealthFlow QA Module - AI Agent mode (Ask / Agent switch, settings, live steps, Stop).

Real browser, real APIs (no model needed: the Agent loop itself is covered by the Django tests with scripted models):
  1. The Ask/Agent switch is on the chat, defaults to Ask, switching to Agent is saved on the server and survives a reload.
  2. Settings > AI Advisor shows the Agent controls (on/off, limits, editable instructions with the default text); a custom text
     and limit are saved through the real API and "Restore default" brings the default back.
  3. The live step list and the Stop button render from a progress payload; clicking Stop calls the real stop endpoint
     (own conversation -> ok, unknown id -> 404).
Every setting it changes is restored at the end.
"""

from tests.modules.e2e_settings import AI_ENGINE_PINS, fresh_state, pinned

MODE_URL, STOP_URL, SETTINGS_URL = "/api/financial-advisor/ai/chat-mode/", "/api/financial-advisor/ai/stop/", "/api/settings/ai/"
_FETCH = """async ([url, method, body]) => {
  const res = await fetch(url, {method, headers: {"Content-Type": "application/json",
    "X-CSRFToken": (window.wfGetCsrfToken && window.wfGetCsrfToken()) || ""}, body: body ? JSON.stringify(body) : undefined});
  let data = null; try { data = await res.json(); } catch (e) {}
  return {status: res.status, data};
}"""
KEYS = ["ai_agent_enabled", "ai_agent_instructions", "ai_agent_max_steps", "ai_agent_budget_s", "ai_agent_max_reads", "ai_chat_mode"]
STEPS = {"status": "running", "can_stop": True, "steps": [
    {"n": 1, "tool": "app_data_models", "label": "Looking at your data tables", "status": "ok", "target": ""},
    {"n": 2, "tool": "app_data_query", "label": "Querying Expense", "status": "running", "target": "Expense"}]}


def _step(reporter, screenshot_logger, page, name, ok, detail, area="ai", shot_name="agent"):
    shot = screenshot_logger.capture(page, area, shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _switch(page, context, reporter, screenshot_logger):
    page.reload()
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-mode-switch", timeout=15000)
    before = page.get_attribute("#ai-ws-mode-ask", "aria-pressed")
    page.click("#ai-ws-mode-agent")
    page.wait_for_timeout(600)
    saved = page.evaluate(_FETCH, [MODE_URL, "GET", None])["data"]
    hint = page.inner_text("#ai-ws-mode-hint")
    page.reload()
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-mode-switch", timeout=15000)
    page.wait_for_function("() => document.getElementById('ai-ws-mode-agent').getAttribute('aria-pressed') === 'true'", timeout=8000)
    ok = before == "true" and saved.get("mode") == "agent" and "Agent" in hint
    _step(reporter, screenshot_logger, page, "AI Agent: Ask/Agent switch is remembered", ok,
          f"default ask pressed={before!r}, server mode={saved.get('mode')!r}, hint={hint!r}, still Agent after reload")


def _live_steps_and_stop(page, context, reporter, screenshot_logger):
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input", timeout=15000)
    conv = page.evaluate(_FETCH, ["/api/financial-advisor/ai/conversations/", "POST", {"title": "E2E agent stop"}])
    conv_id = ((conv["data"] or {}).get("conversation") or conv["data"] or {}).get("id")
    page.evaluate("(id) => { _aiState.conversationId = id; _setLoadingUI(true); }", conv_id)
    page.evaluate("(d) => window._aiRenderAgentSteps(d)", STEPS)
    rows = page.locator("#ai-ws-agent-steps li.ai-ws-agent-step")
    shown = rows.count() == 2 and "ok" in (rows.nth(0).get_attribute("class") or "") and "running" in (rows.nth(1).get_attribute("class") or "")
    has_stop = page.locator("#ai-ws-agent-stop").is_visible()
    shot_ok = shown and has_stop
    with page.expect_request(lambda r: STOP_URL in r.url and r.method == "POST", timeout=8000) as info:
        page.click("#ai-ws-agent-stop")
    sent = info.value.post_data or ""
    _step(reporter, screenshot_logger, page, "AI Agent: live steps and Stop button", shot_ok and str(conv_id) in sent,
          f"steps rendered={shown}, stop visible={has_stop}, stop request body={sent!r}", shot_name="agent_steps")
    page.evaluate("() => _setLoadingUI(false)")
    own = page.evaluate(_FETCH, [STOP_URL, "POST", {"conversation_id": conv_id}])["status"]
    foreign = page.evaluate(_FETCH, [STOP_URL, "POST", {"conversation_id": 99999999}])["status"]
    _step(reporter, screenshot_logger, page, "AI Agent: Stop endpoint is owner-scoped", own == 200 and foreign == 404,
          f"own conversation={own}, unknown conversation={foreign}", shot_name="agent_stop_api")
    if conv_id:
        page.evaluate(_FETCH, [f"/api/financial-advisor/ai/conversations/{conv_id}/", "DELETE", None])


def _settings(page, context, reporter, screenshot_logger):
    context.goto_route("#settings-aiadvisor")
    page.wait_for_selector("#aiAgentInstructionsInput", timeout=20000)
    default_text = page.evaluate(_FETCH, [SETTINGS_URL, "GET", None])["data"]["ai_agent_instructions_default"]
    shows_default = page.input_value("#aiAgentInstructionsInput").strip() == default_text.strip()
    page.fill("#aiAgentInstructionsInput", "E2E RULE: always cite the table.")
    page.fill("#aiAgentMaxStepsInput", "7")
    with page.expect_response(lambda r: SETTINGS_URL in r.url and r.request.method == "POST", timeout=15000):
        page.click("#aiSaveBtn")
    page.wait_for_timeout(600)
    got = page.evaluate(_FETCH, [SETTINGS_URL, "GET", None])["data"]
    saved = got["ai_agent_instructions"] == "E2E RULE: always cite the table." and got["ai_agent_max_steps"] == 7
    page.click("#aiAgentInstructionsResetBtn")
    reset = page.input_value("#aiAgentInstructionsInput").strip() == default_text.strip()
    with page.expect_response(lambda r: SETTINGS_URL in r.url and r.request.method == "POST", timeout=15000):
        page.click("#aiSaveBtn")
    page.wait_for_timeout(600)
    after = page.evaluate(_FETCH, [SETTINGS_URL, "GET", None])["data"]
    _step(reporter, screenshot_logger, page, "AI Agent: settings (instructions + limits)", shows_default and saved and reset and after["ai_agent_instructions"] == "",
          f"default shown={shows_default}, custom saved={saved}, restore default={reset}, stored after restore={after['ai_agent_instructions']!r}",
          area="settings", shot_name="ai_agent_settings")


def _run(context, reporter, screenshot_logger):
    page = context.page
    _switch(page, context, reporter, screenshot_logger)
    _live_steps_and_stop(page, context, reporter, screenshot_logger)
    _settings(page, context, reporter, screenshot_logger)
    page.evaluate(_FETCH, [MODE_URL, "POST", {"mode": "ask"}])


def test_ai_agent(context, reporter, screenshot_logger):
    try:
        with pinned({**AI_ENGINE_PINS, "ai_direct_answers": "true"}), fresh_state(KEYS):
            _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "agent_error", "none", "fail", "fail")
        reporter.add_step("AI Agent mode", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
