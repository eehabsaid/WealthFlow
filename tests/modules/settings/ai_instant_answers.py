"""Settings module phase 7: AI Advisor "Instant Data Answers" toggle (ai_direct_answers) + the instant-answer engine.

Checks, against the real API (not just the DOM):
  1. The toggle renders on #settings-aiadvisor and its stored default is ON.
  2. Unchecking it + Save persists false; checking it + Save persists true (the original state is restored).
  3. With it ON, a plain data question is answered by code: tool_calls[0].direct_answer is true and llm_calls is 0.
  4. With it OFF the same question is NOT answered by the engine (no direct_answer marker). Skipped when the
     AI provider is not configured in this environment (the chat endpoint then refuses before any routing).
"""

SETTINGS_URL = "/api/settings/ai/"
CHAT_URL = "/api/financial-advisor/ai/chat/"
QUESTION = "how much money do I have"   # answered from Balance rows only, valid even for an empty account


def _api_get(page, url):
    return page.evaluate("async (u) => { const r = await fetch(u); return r.ok ? await r.json() : null; }", url)


def _ask(page, text):
    return page.evaluate(
        """async ([url, text]) => {
            const token = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
            const r = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
                                        body: JSON.stringify({message: text})});
            let body = null; try { body = await r.json(); } catch (e) {}
            return {status: r.status, body};
        }""",
        [CHAT_URL, text],
    )


def _direct_call(resp):
    calls = ((resp or {}).get("body") or {}).get("message", {}).get("tool_calls") or []
    return calls[0] if calls and isinstance(calls[0], dict) and calls[0].get("direct_answer") else None


def _set_toggle(context, checked):
    """Click the real toggle + Save button; returns the stored value read back through the API."""
    page = context.page
    box = page.query_selector("#aiDirectAnswersToggle")
    if box is None:
        return None
    if box.is_checked() != checked:
        box.click()
    with page.expect_response(lambda r: SETTINGS_URL in r.url and r.request.method == "POST", timeout=15000):
        page.click("#aiSaveBtn")
    page.wait_for_timeout(500)
    data = _api_get(page, SETTINGS_URL) or {}
    return data.get("ai_direct_answers")


def test_ai_instant_answers(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#settings-aiadvisor")
    reporter.pages_visited.add("Settings -> AI Advisor")
    try:
        page.wait_for_selector("#aiDirectAnswersToggle", timeout=20000)
    except Exception as ex:
        shot = screenshot_logger.capture(page, "settings", "ai_instant_answers", "none", "toggle_missing", "fail")
        reporter.add_step("AI Instant Data Answers Toggle", "Settings", "FAIL", f"Toggle not rendered: {ex}", screenshot_path=shot)
        return

    original = (_api_get(page, SETTINGS_URL) or {}).get("ai_direct_answers")
    shot = screenshot_logger.capture(page, "settings", "ai_instant_answers", "none", "toggle", "ok")
    ok_default = original is True and page.is_checked("#aiDirectAnswersToggle")
    reporter.add_step("AI Instant Data Answers Default ON", "Settings", "PASS" if ok_default else "FAIL",
                      f"API ai_direct_answers={original!r}, checkbox checked={page.is_checked('#aiDirectAnswersToggle')}", screenshot_path=shot)

    try:
        off = _set_toggle(context, False)
        reporter.add_step("AI Instant Data Answers Save OFF", "Settings", "PASS" if off is False else "FAIL", f"API value after save: {off!r}")

        resp_off = _ask(page, QUESTION)
        if resp_off["status"] != 200:
            reporter.add_step("AI Instant Answer Kill Switch", "WealthFlow AI", "SKIP",
                              f"Chat endpoint returned {resp_off['status']} (AI workspace not available for this account: plan or provider); engine path not exercised.")
        else:
            direct = _direct_call(resp_off)
            reporter.add_step("AI Instant Answer Kill Switch", "WealthFlow AI", "PASS" if direct is None else "FAIL",
                              "OFF: question was sent to the model path." if direct is None else "OFF but the engine still answered.")

        on = _set_toggle(context, True)
        reporter.add_step("AI Instant Data Answers Save ON", "Settings", "PASS" if on is True else "FAIL", f"API value after save: {on!r}")

        resp_on = _ask(page, QUESTION)
        if resp_on["status"] != 200:
            reporter.add_step("AI Instant Answer (0 LLM calls)", "WealthFlow AI", "SKIP",
                              f"Chat endpoint returned {resp_on['status']} (AI workspace not available for this account: plan or provider).")
        else:
            call = _direct_call(resp_on)
            passed = bool(call) and call.get("llm_calls") == 0
            reporter.add_step("AI Instant Answer (0 LLM calls)", "WealthFlow AI", "PASS" if passed else "FAIL",
                              f"tool={call.get('tool')!r} llm_calls={call.get('llm_calls')!r}" if call else "Engine did not answer a plain balance question.")
    except Exception as ex:
        reporter.add_step("AI Instant Data Answers", "Settings", "FAIL", f"Exception: {ex}")
    finally:
        try:   # always leave the account in its original state
            if original is not None:
                _set_toggle(context, bool(original))
        except Exception:
            pass
