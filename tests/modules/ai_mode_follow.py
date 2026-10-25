"""Browser contract for "Ask hands a guide request to Agent mode": when the chat response says chat_mode "agent", the Ask/Agent bar
switches to Agent by itself. The chat call is answered by the browser (page.route), so no model is needed; the server side (the
YES/NO question, the saved mode, the file) is covered by core/tests/ai/test_ask_moves_guide_to_agent.py. (No core.* imports.)"""

import json

_REPLY = {"ok": True, "conversation_id": 987654, "message": {"id": 1, "role": "assistant", "content": "Done.", "sources": [], "tool_calls": []},
          "chat_mode": "agent"}


def _bar_mode(page):
    return page.evaluate("document.querySelector('#ai-ws-mode-switch button.active')?.dataset.mode || ''")


def _run(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input", timeout=8000)
    if page.evaluate("document.getElementById('ai-ws-mode-switch')?.hidden !== false"):
        reporter.add_step("AI Ask -> Agent: the mode bar follows the server", "WealthFlow AI", "SKIP", "Agent mode is switched off for this account, so there is no bar")
        return
    page.evaluate("_aiSetChatMode('ask')")
    page.route("**/api/financial-advisor/ai/chat/", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(_REPLY)))
    try:
        before = _bar_mode(page)
        page.fill("#ai-ws-input", "generate the user guide for the entire app as HTML")
        page.keyboard.press("Enter")
        page.wait_for_function("document.querySelector('#ai-ws-mode-switch button.active')?.dataset.mode === 'agent'", timeout=8000)
        after = _bar_mode(page)
    finally:
        page.unroute("**/api/financial-advisor/ai/chat/")
        page.evaluate("_aiSetChatMode('ask')")
    ok = before == "ask" and after == "agent"
    shot = screenshot_logger.capture(page, "ai", "ask_moves_to_agent", "none", "view", "ok" if ok else "fail")
    reporter.add_step("AI Ask -> Agent: the mode bar follows the server", "WealthFlow AI", "PASS" if ok else "FAIL", f"bar {before!r} -> {after!r}", screenshot_path=shot)


def test_ai_mode_follow(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "ask_moves_to_agent_error", "none", "fail", "fail")
        reporter.add_step("AI Ask -> Agent: the mode bar follows the server", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
    finally:
        context.goto_route("#ai")
